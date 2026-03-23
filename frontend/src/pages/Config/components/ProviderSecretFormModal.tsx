import { Form, Input, Modal, Switch } from "antd";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export interface ProviderSecretFormValues {
  id?: string;
  provider: string;
  name: string;
  secret?: string;
  is_active: boolean;
  is_default: boolean;
}

interface ProviderSecretFormModalProps {
  open: boolean;
  loading?: boolean;
  initialValues?: ProviderSecretFormValues;
  onCancel: () => void;
  onSubmit: (values: ProviderSecretFormValues) => Promise<void> | void;
}

export default function ProviderSecretFormModal({
  open,
  loading = false,
  initialValues,
  onCancel,
  onSubmit,
}: ProviderSecretFormModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm<ProviderSecretFormValues>();

  useEffect(() => {
    if (!open) {
      return;
    }
    form.setFieldsValue({
      provider: initialValues?.provider ?? "openai",
      name: initialValues?.name ?? "default",
      secret: "",
      is_active: initialValues?.is_active ?? true,
      is_default: initialValues?.is_default ?? false,
      id: initialValues?.id,
    });
  }, [form, initialValues, open]);

  const handleOk = async () => {
    const values = await form.validateFields();
    const nextValues: ProviderSecretFormValues = {
      ...values,
      secret: values.secret?.trim() || undefined,
    };
    await onSubmit(nextValues);
    form.resetFields();
  };

  return (
    <Modal
      open={open}
      title={initialValues ? t("common.edit") : t("common.create")}
      onCancel={onCancel}
      onOk={() => void handleOk()}
      confirmLoading={loading}
      destroyOnClose
    >
      <Form layout="vertical" form={form}>
        <Form.Item
          name="provider"
          label={t("config.providerSecrets.columns.provider")}
          rules={[{ required: true }]}
        >
          <Input placeholder="openai / anthropic / azure-openai" />
        </Form.Item>
        <Form.Item
          name="name"
          label={t("config.providerSecrets.columns.name")}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="secret"
          label={t("config.providerSecrets.secretValue")}
          rules={initialValues ? [] : [{ required: true }]}
          extra={initialValues ? t("config.providerSecrets.secretOptionalHint") : undefined}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>
        <Form.Item name="is_active" label={t("config.providerSecrets.columns.status")} valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item
          name="is_default"
          label={t("config.providerSecrets.columns.default")}
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
