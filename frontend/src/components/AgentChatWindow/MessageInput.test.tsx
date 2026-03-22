import { fireEvent, render, screen } from "@testing-library/react";
import { jest } from "@jest/globals";

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "chat.placeholder": "Ask something",
        "chat.send": "Send",
      };
      return map[key] ?? key;
    },
  }),
}));

const { MessageInput } = await import("./MessageInput");

describe("MessageInput", () => {
  it("calls onSend with the input value on button click", () => {
    const onSend = jest.fn();
    render(<MessageInput onSend={onSend} disabled={false} />);

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "test query" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(onSend).toHaveBeenCalledWith("test query");
  });

  it("clears the input after sending", () => {
    const onSend = jest.fn();
    render(<MessageInput onSend={onSend} disabled={false} />);

    const input = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(input.value).toBe("");
  });

  it("Enter triggers send", () => {
    const onSend = jest.fn();
    render(<MessageInput onSend={onSend} disabled={false} />);

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "enter test" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(onSend).toHaveBeenCalledWith("enter test");
  });
});
