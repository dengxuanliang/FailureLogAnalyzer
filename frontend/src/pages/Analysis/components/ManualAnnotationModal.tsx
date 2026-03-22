import { useEffect, useState } from "react";
import { App, Input, Modal, Select, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useAnnotateRecord } from "@/api/queries/annotations";

interface ManualAnnotationModalProps {
  open: boolean;
  recordId: string;
  existingTags: string[];
  taxonomyTags: string[];
  onClose: () => void;
}

export function ManualAnnotationModal({
  open,
  recordId,
  existingTags,
  taxonomyTags,
  onClose,
}: ManualAnnotationModalProps) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [selectedTags, setSelectedTags] = useState<string[]>(existingTags);
  const [note, setNote] = useState("");

  const annotateMutation = useAnnotateRecord();

  useEffect(() => {
    if (!open) {
      return;
    }

    setSelectedTags(existingTags);
    setNote("");
  }, [open, existingTags]);

  const handleSubmit = () => {
    annotateMutation.mutate(
      {
        record_id: recordId,
        tags: selectedTags,
        note: note.trim() ? note.trim() : undefined,
      },
      {
        onSuccess: () => {
          message.success(t("annotation.success"));
          onClose();
        },
        onError: () => {
          message.error(t("annotation.error"));
        },
      },
    );
  };

  return (
    <Modal
      title={t("annotation.title")}
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText={t("annotation.submit")}
      cancelText={t("annotation.cancel")}
      confirmLoading={annotateMutation.isPending}
      width={560}
      destroyOnHidden
    >
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Typography.Text type="secondary">
          {t("annotation.description")}
        </Typography.Text>

        <div>
          <Typography.Text strong>{t("annotation.selectTags")}</Typography.Text>
          <Select
            mode="multiple"
            allowClear
            style={{ width: "100%", marginTop: 8 }}
            options={taxonomyTags.map((tag) => ({ label: tag, value: tag }))}
            value={selectedTags}
            onChange={setSelectedTags}
            optionFilterProp="label"
            placeholder={t("annotation.selectTags")}
          />
        </div>

        <div>
          <Typography.Text strong>{t("annotation.note")}</Typography.Text>
          <Input.TextArea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            style={{ marginTop: 8 }}
          />
        </div>
      </Space>
    </Modal>
  );
}
