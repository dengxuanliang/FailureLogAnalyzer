import { useMemo, useState } from "react";
import { Button, Card, Input, Select, Space, Table, Typography } from "antd";
import {
  useIngestJobStatusQueries,
  useIngestUpload,
  useLlmJobStatusQueries,
  useLlmStrategies,
  useTriggerLlmJob,
} from "@/api/queries/operations";

const { Title, Text } = Typography;

export default function Operations() {
  const [benchmark, setBenchmark] = useState("");
  const [model, setModel] = useState("");
  const [modelVersion, setModelVersion] = useState("");
  const [file, setFile] = useState<globalThis.File | null>(null);
  const [latestSessionId, setLatestSessionId] = useState("");
  const [ingestJobIds, setIngestJobIds] = useState<string[]>([]);
  const [llmJobIds, setLlmJobIds] = useState<string[]>([]);

  const ingestUpload = useIngestUpload();
  const triggerLlmJob = useTriggerLlmJob();
  const strategies = useLlmStrategies();
  const ingestQueries = useIngestJobStatusQueries(ingestJobIds);
  const llmQueries = useLlmJobStatusQueries(llmJobIds);

  const ingestJobs = useMemo(
    () => ingestQueries.map((query) => query.data).filter(Boolean),
    [ingestQueries],
  );
  const llmJobs = useMemo(
    () => llmQueries.map((query) => query.data).filter(Boolean),
    [llmQueries],
  );

  const handleUpload = async () => {
    if (!file) {
      return;
    }

    const response = await ingestUpload.mutateAsync({
      file,
      benchmark,
      model,
      model_version: modelVersion,
    });
    setLatestSessionId(response.session_id);
    setIngestJobIds((previous) => [response.job_id, ...previous.filter((jobId) => jobId !== response.job_id)]);
  };

  const handleTriggerLlm = async () => {
    const strategyId = strategies.data?.[0]?.id;
    if (!latestSessionId || !strategyId) {
      return;
    }

    const response = await triggerLlmJob.mutateAsync({
      session_id: latestSessionId,
      strategy_id: strategyId,
    });
    setLlmJobIds((previous) => [response.job_id, ...previous.filter((jobId) => jobId !== response.job_id)]);
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}>Operations Center</Title>

      <Card title="Upload JSONL for Ingestion">
        <Space direction="vertical" style={{ width: "100%" }}>
          <label>
            Benchmark
            <Input aria-label="Benchmark" value={benchmark} onChange={(event) => setBenchmark(event.target.value)} />
          </label>
          <label>
            Model
            <Input aria-label="Model" value={model} onChange={(event) => setModel(event.target.value)} />
          </label>
          <label>
            Model Version
            <Input
              aria-label="Model Version"
              value={modelVersion}
              onChange={(event) => setModelVersion(event.target.value)}
            />
          </label>
          <label>
            JSONL File
            <input
              aria-label="JSONL File"
              type="file"
              accept=".json,.jsonl,application/json"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <Button type="primary" onClick={() => void handleUpload()} loading={ingestUpload.isPending}>
            Upload JSONL
          </Button>
          <label>
            Latest Session
            <Input aria-label="Latest Session" value={latestSessionId} readOnly />
          </label>
          <label>
            LLM Strategy
            <Select
              aria-label="LLM Strategy"
              value={strategies.data?.[0]?.id}
              options={(strategies.data ?? []).map((strategy) => ({
                value: strategy.id,
                label: strategy.name,
              }))}
            />
          </label>
          <Button onClick={() => void handleTriggerLlm()} loading={triggerLlmJob.isPending}>
            Trigger LLM Job
          </Button>
        </Space>
      </Card>

      <Card title="Monitor Ingest + LLM Jobs">
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Text strong>Ingest Jobs</Text>
            <Table
              size="small"
              rowKey="job_id"
              pagination={false}
              dataSource={ingestJobs}
              columns={[
                { title: "Job ID", dataIndex: "job_id", key: "job_id" },
                { title: "Session", dataIndex: "session_id", key: "session_id" },
                { title: "Status", dataIndex: "status", key: "status" },
              ]}
            />
          </div>
          <div>
            <Text strong>LLM Jobs</Text>
            <Table
              size="small"
              rowKey="job_id"
              pagination={false}
              dataSource={llmJobs}
              columns={[
                { title: "Job ID", dataIndex: "job_id", key: "job_id" },
                { title: "Session", dataIndex: "session_id", key: "session_id" },
                { title: "Status", dataIndex: "status", key: "status" },
              ]}
            />
          </div>
        </Space>
      </Card>
    </Space>
  );
}
