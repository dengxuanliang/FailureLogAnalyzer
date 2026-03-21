import { SendOutlined } from "@ant-design/icons";
import { Button, Input, Space } from "antd";
import { useCallback, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

interface MessageInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }

    onSend(trimmed);
    setValue("");
  }, [disabled, onSend, value]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <Space.Compact style={{ padding: 12, width: "100%" }}>
      <Input.TextArea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("chat.placeholder")}
        autoSize={{ minRows: 1, maxRows: 4 }}
        disabled={disabled}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={handleSend}
        aria-label={t("chat.send")}
        disabled={disabled || value.trim().length === 0}
      >
        {t("chat.send")}
      </Button>
    </Space.Compact>
  );
}
