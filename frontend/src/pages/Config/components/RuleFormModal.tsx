import { useEffect } from "react";
import { Form, Input, InputNumber, Modal, Select, Switch } from "antd";
import { useTranslation } from "react-i18next";
import type {
  AnalysisRule,
  RuleConditionType,
} from "@/api/queries/config";

const CONDITION_TYPES: RuleConditionType[] = [
  "regex",
  "contains",
  "not_contains",
  "length_gt",
  "length_lt",
  "field_equals",
  "field_missing",
  "python_expr",
];

interface RuleFormModalProps {
  open: boolean;
  rule: AnalysisRule | null;
  onSubmit: (...args: any[]) => unknown;
  onCancel: () => void;
  loading: boolean;
}

export default function RuleFormModal({
  open,
  rule,
  onSubmit,
  onCancel,
  loading,
}: RuleFormModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();

  useEffect(() => {
    if (!open) {
      return;
    }

    if (rule) {
      form.setFieldsValue({
        name: rule.name,
        description: rule.description,
        field: rule.field,
        condition: rule.condition,
        tags: rule.tags,
        confidence: rule.confidence,
        priority: rule.priority,
        is_active: rule.is_active,
      });
      return;
    }

    form.resetFields();
    form.setFieldsValue({
      condition: { type: "contains" },
      confidence: 0.9,
      priority: 10,
      is_active: true,
    });
  }, [form, open, rule]);

  const handleOk = async () => {
    const values = await form.validateFields();
    await onSubmit(values);
  };

  return (
    <Modal
      open={open}
      title={rule ? t("config.rules.edit") : t("config.rules.create")}
      onOk={() => void handleOk()}
      onCancel={onCancel}
      confirmLoading={loading}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item name="name" label={t("config.rules.form.name")} rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="field" label={t("config.rules.form.field")} rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item
          name={["condition", "type"]}
          label={t("config.rules.form.conditionType")}
          rules={[{ required: true }]}
        >
          <Select options={CONDITION_TYPES.map((value) => ({ value, label: value }))} />
        </Form.Item>
        <Form.Item name={["condition", "pattern"]} label={t("config.rules.form.pattern")}>
          <Input />
        </Form.Item>
        <Form.Item name="tags" label={t("config.rules.form.tags")} rules={[{ required: true }]}>
          <Select mode="tags" tokenSeparators={[","]} />
        </Form.Item>
        <Form.Item name="confidence" label={t("config.rules.form.confidence")} rules={[{ required: true }]}>
          <InputNumber min={0} max={1} step={0.05} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="priority" label={t("config.rules.form.priority")} rules={[{ required: true }]}>
          <InputNumber min={1} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="is_active" label={t("config.rules.form.isActive")} valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
