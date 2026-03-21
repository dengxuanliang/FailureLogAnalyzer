import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { Button, Card, Space, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import type { ErrorRecordBrief } from "../../../types/api";

interface ErrorTableProps {
  records: ErrorRecordBrief[];
  total: number;
  page: number;
  size: number;
  loading: boolean;
  onPageChange: (page: number, size: number) => void;
  onViewDetail: (recordId: string) => void;
}

export default function ErrorTable({
  records,
  total,
  page,
  size,
  loading,
  onPageChange,
  onViewDetail,
}: ErrorTableProps) {
  const { t } = useTranslation();

  const columns: ColumnsType<ErrorRecordBrief> = [
    {
      title: t("analysis.columns.questionId"),
      dataIndex: "question_id",
      key: "question_id",
      width: 120,
      ellipsis: true,
    },
    {
      title: t("analysis.columns.benchmark"),
      dataIndex: "benchmark",
      key: "benchmark",
      width: 120,
    },
    {
      title: t("analysis.columns.category"),
      dataIndex: "task_category",
      key: "task_category",
      width: 120,
      render: (value: ErrorRecordBrief["task_category"]) => value ?? "-",
    },
    {
      title: t("analysis.columns.question"),
      dataIndex: "question",
      key: "question",
      ellipsis: true,
    },
    {
      title: t("analysis.columns.errorTags"),
      dataIndex: "error_tags",
      key: "error_tags",
      width: 240,
      render: (tags: string[]) => (
        <Space size={[0, 4]} wrap>
          {tags.map((tag) => (
            <Tag color="red" key={tag}>
              {tag}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t("analysis.columns.hasLlm"),
      dataIndex: "has_llm_analysis",
      key: "has_llm_analysis",
      width: 100,
      align: "center",
      render: (hasLlm: boolean) =>
        hasLlm ? (
          <CheckCircleOutlined style={{ color: "#52c41a" }} />
        ) : (
          <CloseCircleOutlined style={{ color: "#ff4d4f" }} />
        ),
    },
    {
      title: t("analysis.columns.actions"),
      key: "actions",
      width: 120,
      render: (_value, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => onViewDetail(record.id)}
        >
          {t("analysis.viewDetail")}
        </Button>
      ),
    },
  ];

  return (
    <Card title={t("analysis.recordsTitle")}>
      <Table<ErrorRecordBrief>
        columns={columns}
        dataSource={records}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: size,
          total,
          showSizeChanger: true,
          onChange: onPageChange,
        }}
      />
    </Card>
  );
}
