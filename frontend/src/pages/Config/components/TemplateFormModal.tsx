import { useEffect } from "react";
import { Form, Input, Modal, Switch } from "antd";
import { useTranslation } from "react-i18next";
import type { PromptTemplate } from "@/api/queries/config";

interface TemplateFormModalProps {
  open: boolean;
  template: PromptTemplate | null;
  onSubmit: (...args: any[]) => unknown;
  onCancel: () => void;
  loading: boolean;
}

export default function TemplateFormModal({
  open,
  template,
  onSubmit,
  onCancel,
  loading,
}: TemplateFormModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();

  useEffect(() => {
    if (!open) {
      return;
    }

    if (template) {
      form.setFieldsValue({
        name: template.name,
        benchmark: template.benchmark,
        template: template.template,
        is_active: template.is_active,
      });
      return;
    }

    form.resetFields();
    form.setFieldsValue({ benchmark: null, is_active: true });
  }, [form, open, template]);

  const handleSubmit = async () => {
    const values = await form.validateFields();
    await onSubmit({
      ...values,
      benchmark:
        typeof values.benchmark === "string" && values.benchmark.trim().length === 0
          ? null
          : values.benchmark ?? null,
    });
  };

  return (
    <Modal
      open={open}
      title={template ? t("config.templates.edit") : t("config.templates.create")}
      onOk={() => void handleSubmit()}
      onCancel={onCancel}
      confirmLoading={loading}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item name="name" label={t("config.templates.form.name")} rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="benchmark" label={t("config.templates.form.benchmark")}>
          <Input />
        </Form.Item>
        <Form.Item
          name="template"
          label={t("config.templates.form.template")}
          rules={[{ required: true }]}
        >
          <Input.TextArea rows={6} />
        </Form.Item>
        <Form.Item name="is_active" label={t("config.templates.form.isActive")} valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
