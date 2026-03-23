import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

const hooksMock = {
  useProviderSecrets: jest.fn(),
  useCreateProviderSecret: jest.fn(),
  useUpdateProviderSecret: jest.fn(),
  useDeleteProviderSecret: jest.fn(),
};

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.providerSecrets.title": "Provider 密钥",
        "config.providerSecrets.create": "新增密钥",
        "config.providerSecrets.columns.provider": "Provider",
        "config.providerSecrets.columns.name": "名称",
        "config.providerSecrets.columns.mask": "密钥",
        "config.providerSecrets.columns.status": "状态",
        "config.providerSecrets.columns.default": "默认",
        "config.providerSecrets.columns.actions": "操作",
        "config.providerSecrets.active": "启用",
        "config.providerSecrets.inactive": "停用",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/api/queries/config", () => hooksMock);
await jest.unstable_mockModule("./ProviderSecretFormModal", () => ({
  __esModule: true,
  default: () => null,
}));

const { default: ProviderSecretsPanel } = await import("./ProviderSecretsPanel");

describe("ProviderSecretsPanel", () => {
  beforeEach(() => {
    hooksMock.useProviderSecrets.mockReturnValue({
      data: [
        {
          id: "ps1",
          provider: "openai",
          name: "primary",
          secret_mask: "sk-t...3456",
          is_active: true,
          is_default: true,
          created_by: "admin",
          created_at: "2026-03-23",
          updated_at: "2026-03-23",
        },
      ],
      isLoading: false,
    });
    hooksMock.useCreateProviderSecret.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useUpdateProviderSecret.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useDeleteProviderSecret.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
  });

  it("renders provider secret rows", () => {
    render(<ProviderSecretsPanel />);

    expect(screen.getByText("Provider 密钥")).toBeInTheDocument();
    expect(screen.getByText("openai")).toBeInTheDocument();
    expect(screen.getByText("primary")).toBeInTheDocument();
    expect(screen.getByText("sk-t...3456")).toBeInTheDocument();
  });
});
