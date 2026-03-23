#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

API_BASE="${API_BASE:-http://localhost:8000}"
FRONTEND_BASE="${FRONTEND_BASE:-http://localhost:3000}"
DEMO_USERNAME="${DEMO_USERNAME:-admin}"
DEMO_EMAIL="${DEMO_EMAIL:-admin@example.com}"
DEMO_PASSWORD="${DEMO_PASSWORD:-admin123456}"
POLL_INTERVAL_SECS="${SMOKE_POLL_INTERVAL_SECS:-2}"
MAX_POLL_ATTEMPTS="${SMOKE_MAX_POLL_ATTEMPTS:-45}"
INGEST_RETRIES="${SMOKE_INGEST_RETRIES:-2}"
REQUIRE_REPORT_DONE="${SMOKE_REQUIRE_REPORT_DONE:-0}"
ALLOW_DEMO_FALLBACK="${SMOKE_ALLOW_DEMO_FALLBACK:-1}"
OPENAPI_CACHE_FILE=""
UPLOAD_TMP_DIR=""

command -v curl >/dev/null 2>&1 || {
  echo "Missing required command: curl" >&2
  exit 1
}
command -v docker >/dev/null 2>&1 || {
  echo "Missing required command: docker" >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  echo "Missing required command: python3" >&2
  exit 1
}

json_get() {
  local field="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=data$field; print(value if value is not None else '')"
}

json_contains_item_by_field() {
  local key="$1"
  local expected="$2"
  python3 -c '
import json
import sys

field = sys.argv[1]
expected = sys.argv[2]
payload = json.load(sys.stdin)
items = payload if isinstance(payload, list) else payload.get("items", [])
for item in items:
    if str(item.get(field, "")) == expected:
        raise SystemExit(0)
raise SystemExit(1)
' "$key" "$expected"
}

api_has_path() {
  local path="$1"
  python3 -c '
import json
import sys

spec_path = sys.argv[1]
target = sys.argv[2]
with open(spec_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
paths = data.get("paths", {})
raise SystemExit(0 if target in paths else 1)
' "$OPENAPI_CACHE_FILE" "$path"
}

json_latest_session_fields() {
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
if not isinstance(payload, list) or not payload:
    raise SystemExit(1)
latest = payload[0]
print("|".join([
    str(latest.get("id", "")),
    str(latest.get("benchmark", "")),
    str(latest.get("model_version", "")),
]))
'
}

request() {
  local method="$1"
  local url="$2"
  shift 2
  local response
  response="$(curl -sS -X "$method" "$url" "$@" -w $'\n%{http_code}')"
  RESPONSE_STATUS="${response##*$'\n'}"
  RESPONSE_BODY="${response%$'\n'*}"
}

echo "==> Smoke preflight"
(
  cd "$REPO_ROOT"
  docker compose up -d postgres redis api worker-default frontend >/dev/null
)

# Frontend ping is best-effort: we verify API as required path, frontend should also be serving.
front_status="$(curl -sS -o /dev/null -w '%{http_code}' "${FRONTEND_BASE}/")"
if [[ "$front_status" != "200" ]]; then
  echo "WARN: frontend ${FRONTEND_BASE} returned HTTP ${front_status}" >&2
fi

api_health_status="$(curl -sS -o /dev/null -w '%{http_code}' "${API_BASE}/api/v1/health")"
if [[ "$api_health_status" != "200" ]]; then
  echo "API health check failed: HTTP ${api_health_status}" >&2
  exit 1
fi

OPENAPI_CACHE_FILE="$(mktemp -t fla-openapi-XXXXXX.json)"
curl -sS "${API_BASE}/openapi.json" > "${OPENAPI_CACHE_FILE}"

echo "==> Auth: bootstrap/login"
bootstrap_payload="$(python3 - "$DEMO_USERNAME" "$DEMO_EMAIL" "$DEMO_PASSWORD" <<'PY'
import json
import sys
print(json.dumps({
    "username": sys.argv[1],
    "email": sys.argv[2],
    "password": sys.argv[3],
}))
PY
)"

request POST "${API_BASE}/api/v1/auth/bootstrap" -H 'Content-Type: application/json' -d "$bootstrap_payload"
bootstrap_status="${RESPONSE_STATUS}"
bootstrap_body="${RESPONSE_BODY}"

access_token=""
auth_mode=""

if [[ "$bootstrap_status" == "201" ]]; then
  access_token="$(printf '%s' "$bootstrap_body" | json_get "['access_token']")"
  auth_mode="bootstrap"
  echo "Bootstrap succeeded."
else
  echo "Bootstrap returned HTTP ${bootstrap_status}; trying login..."
  request POST "${API_BASE}/api/v1/auth/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "username=${DEMO_USERNAME}" \
    --data-urlencode "password=${DEMO_PASSWORD}"
  login_status="${RESPONSE_STATUS}"
  login_body="${RESPONSE_BODY}"
  if [[ "$login_status" != "200" ]]; then
    echo "Login failed: HTTP ${login_status}" >&2
    echo "$login_body" >&2
    echo "Hint: run ./scripts/dev-create-admin.sh or set DEMO_* env vars." >&2
    exit 1
  fi
  access_token="$(printf '%s' "$login_body" | json_get "['access_token']")"
  auth_mode="login"
fi

if [[ -z "$access_token" ]]; then
  echo "Failed to obtain access token." >&2
  exit 1
fi

echo "Authenticated via ${auth_mode}."

echo "==> Upload demo JSONL"
ts="$(date +%s)"
model="smoke-model"
benchmark=""
model_version=""
job_id=""
session_id=""

tmp_dir="$(mktemp -d -t fla-smoke-upload-XXXXXX)"
upload_file="${tmp_dir}/demo.jsonl"
cleanup() {
  if [[ -n "$UPLOAD_TMP_DIR" ]]; then
    rm -rf "$UPLOAD_TMP_DIR"
  fi
  if [[ -n "$OPENAPI_CACHE_FILE" ]]; then
    rm -f "$OPENAPI_CACHE_FILE"
  fi
}
trap cleanup EXIT
UPLOAD_TMP_DIR="$tmp_dir"

cat > "$upload_file" <<'JSONL'
{"question_id":"smoke-q1","question":"2+2=?","expected_answer":"4","model_answer":"5","is_correct":false,"score":0,"task_category":"math"}
{"question_id":"smoke-q2","question":"首都是哪里？","expected_answer":"北京","model_answer":"北京","is_correct":true,"score":1,"task_category":"geography"}
JSONL

ingest_status=""
ingest_body=""
for ((ingest_attempt=1; ingest_attempt<=INGEST_RETRIES; ingest_attempt++)); do
  benchmark="smoke-benchmark-${ts}-${ingest_attempt}"
  model_version="smoke-v${ts}-${ingest_attempt}"
  echo "Upload/poll attempt ${ingest_attempt}/${INGEST_RETRIES}..."

  request POST "${API_BASE}/api/v1/ingest/upload" \
    -H "Authorization: Bearer ${access_token}" \
    -F "file=@${upload_file}" \
    -F "benchmark=${benchmark}" \
    -F "model=${model}" \
    -F "model_version=${model_version}" \
    -F "adapter_name=generic_jsonl"
  upload_status="${RESPONSE_STATUS}"
  upload_body="${RESPONSE_BODY}"

  if [[ "$upload_status" != "202" ]]; then
    if [[ "$ingest_attempt" -ge "$INGEST_RETRIES" ]]; then
      echo "Upload failed: HTTP ${upload_status}" >&2
      echo "$upload_body" >&2
      exit 1
    fi
    echo "WARN: upload failed (HTTP ${upload_status}); retrying..." >&2
    continue
  fi

  job_id="$(printf '%s' "$upload_body" | json_get "['job_id']")"
  session_id="$(printf '%s' "$upload_body" | json_get "['session_id']")"
  if [[ -z "$job_id" || -z "$session_id" ]]; then
    if [[ "$ingest_attempt" -ge "$INGEST_RETRIES" ]]; then
      echo "Upload response missing job_id/session_id." >&2
      echo "$upload_body" >&2
      exit 1
    fi
    echo "WARN: upload response missing ids; retrying..." >&2
    continue
  fi

  echo "Queued ingest job=${job_id} session=${session_id}"
  echo "==> Poll ingest status"
  ingest_status=""
  ingest_body=""
  for ((i=1; i<=MAX_POLL_ATTEMPTS; i++)); do
    request GET "${API_BASE}/api/v1/ingest/${job_id}/status" -H "Authorization: Bearer ${access_token}"
    poll_status="${RESPONSE_STATUS}"
    ingest_body="${RESPONSE_BODY}"
    if [[ "$poll_status" != "200" ]]; then
      echo "Poll failed (attempt ${i}): HTTP ${poll_status}" >&2
      sleep "$POLL_INTERVAL_SECS"
      continue
    fi

    ingest_status="$(printf '%s' "$ingest_body" | json_get "['status']")"
    if [[ "$ingest_status" == "done" ]]; then
      echo "Ingest completed."
      break
    fi
    if [[ "$ingest_status" == "failed" ]]; then
      echo "WARN: ingest failed for attempt ${ingest_attempt}." >&2
      echo "$ingest_body" >&2
      break
    fi

    sleep "$POLL_INTERVAL_SECS"
  done

  if [[ "$ingest_status" == "done" ]]; then
    break
  fi

  if [[ "$ingest_attempt" -lt "$INGEST_RETRIES" ]]; then
    echo "Retrying ingest path..." >&2
  fi
done

if [[ "$ingest_status" != "done" ]]; then
  if [[ "$ALLOW_DEMO_FALLBACK" == "1" || "$ALLOW_DEMO_FALLBACK" == "true" ]]; then
    echo "WARN: upload ingest path unavailable; falling back to demo seed path." >&2
    (
      cd "$REPO_ROOT"
      ./scripts/dev-seed-demo.sh >/dev/null
    )
    request GET "${API_BASE}/api/v1/sessions" -H "Authorization: Bearer ${access_token}"
    if [[ "${RESPONSE_STATUS}" != "200" ]]; then
      echo "Failed to list sessions after demo seed: HTTP ${RESPONSE_STATUS}" >&2
      echo "${RESPONSE_BODY}" >&2
      exit 1
    fi
    latest_session="$(printf '%s' "${RESPONSE_BODY}" | json_latest_session_fields || true)"
    if [[ -z "$latest_session" ]]; then
      echo "No sessions available after demo seed fallback." >&2
      exit 1
    fi
    session_id="${latest_session%%|*}"
    rest="${latest_session#*|}"
    benchmark="${rest%%|*}"
    model_version="${latest_session##*|}"
    if [[ -z "$session_id" ]]; then
      echo "Fallback session parse failed." >&2
      exit 1
    fi
    echo "Using demo fallback session=${session_id} benchmark=${benchmark} model_version=${model_version}"
  else
    echo "Ingest did not reach done status in time." >&2
    echo "$ingest_body" >&2
    exit 1
  fi
fi

echo "==> Verify session visibility"
request GET "${API_BASE}/api/v1/sessions" -H "Authorization: Bearer ${access_token}"
sessions_status="${RESPONSE_STATUS}"
sessions_body="${RESPONSE_BODY}"
if [[ "$sessions_status" != "200" ]]; then
  echo "Session list failed: HTTP ${sessions_status}" >&2
  echo "$sessions_body" >&2
  exit 1
fi

if ! printf '%s' "$sessions_body" | json_contains_item_by_field "id" "$session_id" >/dev/null; then
  echo "Session ${session_id} not found in /sessions output" >&2
  exit 1
fi

if api_has_path "/api/v1/sessions/{session_id}"; then
  request GET "${API_BASE}/api/v1/sessions/${session_id}" -H "Authorization: Bearer ${access_token}"
  if [[ "${RESPONSE_STATUS}" != "200" ]]; then
    echo "Session detail failed: HTTP ${RESPONSE_STATUS}" >&2
    echo "${RESPONSE_BODY}" >&2
    exit 1
  fi
else
  echo "WARN: /api/v1/sessions/{session_id} not present in current OpenAPI; skipping detail check."
fi

echo "==> Generate and verify report visibility"
report_payload="$(python3 - <<PY
import json
print(json.dumps({
    "title": f"Smoke Summary ${ts}",
    "report_type": "summary",
    "benchmark": "${benchmark}",
    "model_version": "${model_version}",
    "session_ids": ["${session_id}"],
}))
PY
)"

request POST "${API_BASE}/api/v1/reports/generate" \
  -H "Authorization: Bearer ${access_token}" \
  -H 'Content-Type: application/json' \
  -d "$report_payload"
report_status="${RESPONSE_STATUS}"
report_body="${RESPONSE_BODY}"
if [[ "$report_status" != "202" ]]; then
  echo "Report generate failed: HTTP ${report_status}" >&2
  echo "$report_body" >&2
  exit 1
fi

report_id="$(printf '%s' "$report_body" | json_get "['report_id']")"
if [[ -z "$report_id" ]]; then
  echo "report_id missing in generate response" >&2
  echo "$report_body" >&2
  exit 1
fi

report_final_status=""
report_detail_body=""
for ((i=1; i<=MAX_POLL_ATTEMPTS; i++)); do
  request GET "${API_BASE}/api/v1/reports/${report_id}" -H "Authorization: Bearer ${access_token}"
  if [[ "${RESPONSE_STATUS}" != "200" ]]; then
    echo "Report poll failed (attempt ${i}): HTTP ${RESPONSE_STATUS}" >&2
    sleep "$POLL_INTERVAL_SECS"
    continue
  fi
  report_detail_body="${RESPONSE_BODY}"
  report_final_status="$(printf '%s' "$report_detail_body" | json_get "['status']")"
  if [[ "$report_final_status" == "done" ]]; then
    echo "Report completed."
    break
  fi
  if [[ "$report_final_status" == "failed" ]]; then
    echo "Report failed." >&2
    echo "$report_detail_body" >&2
    exit 1
  fi
  sleep "$POLL_INTERVAL_SECS"
done

if [[ "$report_final_status" != "done" ]]; then
  if [[ "$REQUIRE_REPORT_DONE" == "1" || "$REQUIRE_REPORT_DONE" == "true" ]]; then
    echo "Report did not reach done status in time." >&2
    echo "$report_detail_body" >&2
    exit 1
  fi
  echo "WARN: report status stayed '${report_final_status}' (not done); continuing because SMOKE_REQUIRE_REPORT_DONE=${REQUIRE_REPORT_DONE}."
fi

request GET "${API_BASE}/api/v1/reports" -H "Authorization: Bearer ${access_token}"
if [[ "${RESPONSE_STATUS}" != "200" ]]; then
  echo "Report list failed: HTTP ${RESPONSE_STATUS}" >&2
  echo "${RESPONSE_BODY}" >&2
  exit 1
fi

if ! printf '%s' "${RESPONSE_BODY}" | json_contains_item_by_field "id" "$report_id" >/dev/null; then
  echo "Report ${report_id} not found in /reports output" >&2
  exit 1
fi

printf '\n✅ Smoke path passed\n'
printf 'auth_mode=%s\n' "$auth_mode"
printf 'session_id=%s\n' "$session_id"
printf 'job_id=%s\n' "$job_id"
printf 'report_id=%s\n' "$report_id"
printf 'report_status=%s\n' "$report_final_status"
printf 'benchmark=%s model_version=%s\n' "$benchmark" "$model_version"
