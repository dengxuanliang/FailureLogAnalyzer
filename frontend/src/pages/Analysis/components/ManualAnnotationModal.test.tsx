import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { App as AntdApp } from "antd";

const mockMutate = jest.fn();

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.unstable_mockModule("@/api/queries/annotations", () => ({
  useAnnotateRecord: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

const { ManualAnnotationModal } = await import("./ManualAnnotationModal");

const taxonomyTags = [
  "格式性错误.空回答",
  "格式性错误.格式不符",
  "推理性错误.逻辑推理.推理链断裂",
];

const renderModal = (open: boolean, onClose = jest.fn()) =>
  render(
    <AntdApp>
      <ManualAnnotationModal
        open={open}
        recordId="rec-1"
        existingTags={["格式性错误.空回答"]}
        taxonomyTags={taxonomyTags}
        onClose={onClose}
      />
    </AntdApp>,
  );

describe("ManualAnnotationModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders modal content when open", () => {
    renderModal(true);

    expect(screen.getByText("annotation.title")).toBeInTheDocument();
    expect(screen.getByText("annotation.selectTags")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    renderModal(false);

    expect(screen.queryByText("annotation.title")).not.toBeInTheDocument();
  });

  it("calls onClose when cancel clicked", () => {
    const onClose = jest.fn();
    renderModal(true, onClose);

    const cancelButton = screen.getByRole("button", { name: "annotation.cancel" });
    fireEvent.click(cancelButton);

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
