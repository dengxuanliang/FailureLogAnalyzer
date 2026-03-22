import { FormEvent, useState } from "react";
import { Alert, Button, Card, Input, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, loading } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await login(username, password);
      navigate("/overview");
    } catch {
      setError(t("login.failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Card style={{ width: 360 }}>
        <Typography.Title level={3}>{t("login.title")}</Typography.Title>

        {error ? (
          <Alert
            role="alert"
            style={{ marginBottom: 16 }}
            type="error"
            message={error}
            showIcon
          />
        ) : null}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label>
              {t("login.username")}
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </label>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label>
              {t("login.password")}
              <Input.Password
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </label>
          </div>

          <Button
            type="primary"
            htmlType="submit"
            block
            loading={submitting}
            disabled={loading}
            aria-label={t("login.submit")}
          >
            {t("login.submit")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
