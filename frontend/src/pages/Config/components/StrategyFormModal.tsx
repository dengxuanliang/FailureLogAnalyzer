import { useEffect } from "react";
import { Form, Input, InputNumber, Modal, Select, Switch } from "antd";
import { useTranslation } from "react-i18next";
import {
  type AnalysisStrategy,
  type LLMStrategyType,
  useTemplates,
} from "@/api/queries/config";

const STRATEGY_TYPES: LLMStrategyType[] = ["full", "fallback", "sample", "manual"];

interface StrategyFormModalProps {
  open: boolean;
  strategy: AnalysisStrategy | null;
  onSubmit: (...args: any[]) => unknown;
  onCancel: () => void;
  loading: boolean;
}

export default function StrategyFormModal({
  open,
  strategy,
  onSubmit,
  onCancel,
  loading,
}: StrategyFormModalProps) {
  const { t } = useTranslation();
  const { data: templates = [] } = useTemplates();
  const [form] = Form.useForm();

  useEffect(() => {
    if (!open) {
      return;
    }

    if (strategy) {
      form.setFieldsValue({
        name: strategy.name,
        strategy_type: strategy.strategy_type,
        config: strategy.config,
        llm_provider: strategy.llm_provider,
        llm_model: strategy.llm_model,
        prompt_template_id: strategy.prompt_template_id,
        max_concurrent: strategy.max_concurrent,
        daily_budget: strategy.daily_budget,
        is_active: strategy.is_active,
      });
      return;
    }

    form.resetFields();
    form.setFieldsValue({
      strategy_type: "fallback",
      max_concurrent: 5,
      daily_budget: 10,
      is_active: true,
      config: {},
    });
  }, [form, open, strategy]);

  const handleSubmit = async () => {
    const values = await form.validateFields();
    await onSubmit({
      ...values,
      prompt_template_id: values.prompt_template_id ?? null,
      config: {},
    });
  };

  return (
    <Modal
      open={open}
      title={strategy ? t("config.strategies.edit") : t("config.strategies.create")}
      onOk={() => void handleSubmit()}
      onCancel={onCancel}
      confirmLoading={loading}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label={t("config.strategies.form.name")}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="strategy_type"
          label={t("config.strategies.form.type")}
          rules={[{ required: true }]}
        >
          <Select options={STRATEGY_TYPES.map((value) => ({ value, label: value }))} />
        </Form.Item>
        <Form.Item
          name="llm_provider"
          label={t("config.strategies.form.provider")}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="llm_model"
          label={t("config.strategies.form.model")}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
        <Form.Item name="prompt_template_id" label="Prompt Template">
          <Select
            allowClear
            options={templates.map((template) => ({ value: template.id, label: template.name }))}
          />
        </Form.Item>
        <Form.Item
          name="max_concurrent"
          label={t("config.strategies.form.maxConcurrent")}
          rules={[{ required: true }]}
        >
          <InputNumber min={1} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item
          name="daily_budget"
          label={t("config.strategies.form.dailyBudget")}
          rules={[{ required: true }]}
        >
          <InputNumber min={0} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item
          name="is_active"
          label={t("config.strategies.form.isActive")}
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
