import { useEffect } from "react";
import { Form, Input, Modal, Select } from "antd";
import { useTranslation } from "react-i18next";
import type { UserCreate, UserRole, UserUpdate } from "@/api/queries/config";

interface UserFormModalProps {
  open: boolean;
  onSubmit: (...args: any[]) => unknown;
  onCancel: () => void;
  initialValues?: { id: string; username: string; email: string; role: UserRole };
  loading?: boolean;
}

const ROLES: UserRole[] = ["admin", "analyst", "viewer"];

export default function UserFormModal({
  open,
  onSubmit,
  onCancel,
  initialValues,
  loading = false,
}: UserFormModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const isEdit = Boolean(initialValues);

  useEffect(() => {
    if (!open) {
      return;
    }

    if (initialValues) {
      form.setFieldsValue({ ...initialValues, password: "" });
      return;
    }

    form.resetFields();
    form.setFieldsValue({ role: "analyst" });
  }, [form, initialValues, open]);

  const handleOk = async () => {
    const values = await form.validateFields();

    if (initialValues) {
      const payload: UserUpdate & { id: string } = {
        id: initialValues.id,
        email: values.email,
        role: values.role,
      };

      if (values.password) {
        payload.password = values.password;
      }

      await onSubmit(payload);
      return;
    }

    await onSubmit(values as UserCreate);
  };

  return (
    <Modal
      open={open}
      title={isEdit ? t("config.users.edit") : t("config.users.create")}
      onOk={() => void handleOk()}
      onCancel={onCancel}
      confirmLoading={loading}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="username"
          label={t("config.users.form.username")}
          rules={[{ required: true }]}
        >
          <Input disabled={isEdit} />
        </Form.Item>
        <Form.Item
          name="email"
          label={t("config.users.form.email")}
          rules={[{ required: true, type: "email" }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="password"
          label={t("config.users.form.password")}
          rules={isEdit ? [] : [{ required: true }]}
        >
          <Input.Password />
        </Form.Item>
        <Form.Item name="role" label={t("config.users.form.role")} rules={[{ required: true }]}>
          <Select>
            {ROLES.map((role) => (
              <Select.Option key={role} value={role}>
                {t(`config.users.role.${role}`)}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
      </Form>
    </Modal>
  );
}
