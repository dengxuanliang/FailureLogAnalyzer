import {
  Card,
  Descriptions,
  Divider,
  Drawer,
  Space,
  Tag,
  Typography,
} from "antd";
import { useTranslation } from "react-i18next";
import type {
  AnalysisResultDetail,
  RecordDetail as RecordDetailType,
} from "../../../types/api";

const { Paragraph, Text } = Typography;

interface RecordDetailProps {
  detail: RecordDetailType | null;
  open: boolean;
  onClose: () => void;
}

function AnalysisCard({ result }: { result: AnalysisResultDetail }) {
  const { t } = useTranslation();

  return (
    <Card
      size="small"
      title={
        <Space>
          <Tag color={result.analysis_type === "llm" ? "blue" : "green"}>
            {result.analysis_type.toUpperCase()}
          </Tag>
          <Text type="secondary">
            {t("analysis.detail.analysisType")}: {result.analysis_type}
          </Text>
        </Space>
      }
      style={{ marginBottom: 12 }}
    >
      <Descriptions column={2} size="small" bordered>
        {result.root_cause ? (
          <Descriptions.Item label={t("analysis.detail.rootCause")} span={2}>
            {result.root_cause}
          </Descriptions.Item>
        ) : null}
        {result.severity ? (
          <Descriptions.Item label={t("analysis.detail.severity")}>
            <Tag
              color={
                result.severity === "high"
                  ? "red"
                  : result.severity === "medium"
                    ? "orange"
                    : "green"
              }
            >
              {result.severity}
            </Tag>
          </Descriptions.Item>
        ) : null}
        {result.confidence != null ? (
          <Descriptions.Item label={t("analysis.detail.confidence")}>
            {(result.confidence * 100).toFixed(1)}%
          </Descriptions.Item>
        ) : null}
        {result.evidence ? (
          <Descriptions.Item label={t("analysis.detail.evidence")} span={2}>
            {result.evidence}
          </Descriptions.Item>
        ) : null}
        {result.suggestion ? (
          <Descriptions.Item label={t("analysis.detail.suggestion")} span={2}>
            {result.suggestion}
          </Descriptions.Item>
        ) : null}
        {result.llm_model ? (
          <Descriptions.Item label={t("analysis.detail.llmModel")}>
            {result.llm_model}
          </Descriptions.Item>
        ) : null}
        {result.llm_cost != null ? (
          <Descriptions.Item label={t("analysis.detail.llmCost")}>
            ${result.llm_cost.toFixed(4)}
          </Descriptions.Item>
        ) : null}
      </Descriptions>
    </Card>
  );
}

export default function RecordDetail({ detail, open, onClose }: RecordDetailProps) {
  const { t } = useTranslation();

  if (!detail || !open) {
    return null;
  }

  const { record, analysis_results, error_tags } = detail;

  return (
    <Drawer title={t("analysis.detail.title")} open={open} onClose={onClose} width={720}>
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label={t("analysis.detail.question")}>
          <Paragraph style={{ marginBottom: 0 }}>{String(record.question ?? "")}</Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label={t("analysis.detail.expected")}>
          <Paragraph style={{ marginBottom: 0 }}>
            {String(record.expected_answer ?? "")}
          </Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label={t("analysis.detail.modelAnswer")}>
          <Paragraph style={{ marginBottom: 0 }}>
            {String(record.model_answer ?? "")}
          </Paragraph>
        </Descriptions.Item>
      </Descriptions>

      <Divider orientation="left">{t("analysis.detail.errorTags")}</Divider>
      <Space size={[4, 8]} wrap>
        {error_tags.map((tag, index) => (
          <Tag color="red" key={`${index}-${String(tag.tag_path ?? index)}`}>
            {String(tag.tag_path ?? "")}
          </Tag>
        ))}
      </Space>

      <Divider orientation="left">{t("analysis.detail.analysisResults")}</Divider>
      {analysis_results.map((result) => (
        <AnalysisCard key={result.id} result={result} />
      ))}
    </Drawer>
  );
}
