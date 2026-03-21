import { useState } from "react";
import {
  Button,
  Card,
  Descriptions,
  Divider,
  Drawer,
  Space,
  Tag,
  Typography,
} from "antd";
import { EditOutlined, SyncOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import apiClient from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { useJobNotifications } from "@/hooks/useJobNotifications";
import type {
  AnalysisResultDetail,
  RecordDetail as RecordDetailType,
} from "../../../types/api";
import { ManualAnnotationModal } from "./ManualAnnotationModal";

const { Paragraph, Text } = Typography;

const KNOWN_TAXONOMY_PATHS = [
  "格式性错误.输出格式不符",
  "格式性错误.JSON解析失败",
  "格式性错误.空回答",
  "格式性错误.语言不符",
  "格式性错误.答案过长截断",
  "提取性错误.代码提取为空",
  "提取性错误.代码提取不完整",
  "提取性错误.答案提取错误",
  "提取性错误.提取字段类型不符",
  "知识性错误.事实错误.核心知识点错误",
  "知识性错误.事实错误.边界知识缺失",
  "知识性错误.事实错误.知识时效性",
  "知识性错误.概念混淆",
  "知识性错误.领域知识盲区",
  "推理性错误.逻辑推理.推理链断裂",
  "推理性错误.逻辑推理.因果推断错误",
  "推理性错误.逻辑推理.缺少关键条件",
  "推理性错误.数学计算.算术错误",
  "推理性错误.数学计算.公式应用错误",
  "推理性错误.数学计算.单位量级错误",
  "推理性错误.多步推理退化",
  "理解性错误.题意理解错误",
  "理解性错误.指令遵循失败",
  "理解性错误.上下文遗漏",
  "理解性错误.歧义理解偏差",
  "生成质量.幻觉",
  "生成质量.重复生成",
  "生成质量.回答不完整",
  "生成质量.过度对齐",
] as const;

const asString = (value: unknown): string => {
  if (typeof value === "string") {
    return value;
  }
  if (value == null) {
    return "";
  }
  return String(value);
};

const getRecordId = (record: Record<string, unknown>): string => asString(record.id);

const extractTagPath = (tag: Record<string, unknown>): string =>
  typeof tag.tag_path === "string" ? tag.tag_path : asString(tag.tag_path);

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
  const { user } = useAuth();
  const [annotateOpen, setAnnotateOpen] = useState(false);
  const [reanalyzePending, setReanalyzePending] = useState(false);
  const [llmJobId, setLlmJobId] = useState<string | null>(null);

  useJobNotifications(llmJobId, "llm");

  if (!detail || !open) {
    return null;
  }

  const { record, analysis_results, error_tags } = detail;
  const recordId = getRecordId(record);
  const existingTags = error_tags.map((tag) => extractTagPath(tag)).filter(Boolean);

  const handleReanalyze = async () => {
    if (!recordId) {
      return;
    }

    setReanalyzePending(true);
    try {
      const response = await apiClient.post<{ job_id?: string }>("/llm/trigger", {
        record_ids: [recordId],
        strategy: "manual",
      });
      setLlmJobId(response.data.job_id ?? null);
    } catch {
      // surface failure via existing query error handling/toasts in future task
    } finally {
      setReanalyzePending(false);
    }
  };

  return (
    <Drawer title={t("analysis.detail.title")} open={open} onClose={onClose} width={720}>
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label={t("analysis.detail.question")}>
          <Paragraph style={{ marginBottom: 0 }}>{asString(record.question)}</Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label={t("analysis.detail.expected")}>
          <Paragraph style={{ marginBottom: 0 }}>{asString(record.expected_answer)}</Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label={t("analysis.detail.modelAnswer")}>
          <Paragraph style={{ marginBottom: 0 }}>{asString(record.model_answer)}</Paragraph>
        </Descriptions.Item>
      </Descriptions>

      <Divider orientation="left">{t("analysis.detail.errorTags")}</Divider>
      <Space size={[4, 8]} wrap>
        {error_tags.map((tag, index) => (
          <Tag color="red" key={`${index}-${extractTagPath(tag) || index}`}>
            {extractTagPath(tag)}
          </Tag>
        ))}
      </Space>

      <Divider orientation="left">{t("analysis.detail.analysisResults")}</Divider>
      {analysis_results.map((result) => (
        <AnalysisCard key={result.id} result={result} />
      ))}

      <Divider />
      <Space>
        <Button
          icon={<EditOutlined />}
          onClick={() => setAnnotateOpen(true)}
          disabled={user?.role === "viewer"}
        >
          {t("analysis.detail.annotate")}
        </Button>
        <Button
          icon={<SyncOutlined />}
          onClick={() => void handleReanalyze()}
          loading={reanalyzePending}
          disabled={user?.role === "viewer"}
        >
          {t("analysis.detail.reanalyze")}
        </Button>
      </Space>

      {annotateOpen && recordId ? (
        <ManualAnnotationModal
          open={annotateOpen}
          recordId={recordId}
          existingTags={existingTags}
          taxonomyTags={[...KNOWN_TAXONOMY_PATHS]}
          onClose={() => setAnnotateOpen(false)}
        />
      ) : null}
    </Drawer>
  );
}
