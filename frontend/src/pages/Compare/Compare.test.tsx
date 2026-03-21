import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";

const mockUseSessions = jest.fn();
const mockUseVersionComparison = jest.fn();
const mockUseVersionDiff = jest.fn();
const mockUseRadarData = jest.fn();

const originalMatchMedia = window.matchMedia;

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: ((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(() => false),
    })) as typeof window.matchMedia,
  });
});

afterAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: originalMatchMedia,
  });
});

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "compare.title": "版本对比",
        "compare.noVersions": "请先选择两个版本",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("../../api/queries/sessions", () => ({
  useSessions: mockUseSessions,
}));

jest.unstable_mockModule("../../api/queries/compare", () => ({
  useVersionComparison: mockUseVersionComparison,
  useVersionDiff: mockUseVersionDiff,
  useRadarData: mockUseRadarData,
}));

jest.unstable_mockModule("./components/VersionSelector", () => ({
  default: ({ versions, onVersionAChange, onVersionBChange, onCompare }: { versions: string[]; onVersionAChange: (v: string) => void; onVersionBChange: (v: string) => void; onCompare: () => void }) => (
    <div>
      <div>versions:{versions.join(",")}</div>
      <button type="button" onClick={() => onVersionAChange("v1.0")}>select-a</button>
      <button type="button" onClick={() => onVersionBChange("v2.0")}>select-b</button>
      <button type="button" onClick={onCompare}>compare</button>
    </div>
  ),
}));

jest.unstable_mockModule("./components/RadarChart", () => ({
  default: () => <div>能力雷达图</div>,
}));

jest.unstable_mockModule("./components/DiffSummary", () => ({
  default: () => <div>变化摘要</div>,
}));

const { default: Compare } = await import("./index");

const comparison = {
  version_a: "v1.0",
  version_b: "v2.0",
  benchmark: null,
  metrics_a: { total: 100, errors: 30, accuracy: 0.7, error_type_distribution: {} },
  metrics_b: { total: 100, errors: 20, accuracy: 0.8, error_type_distribution: {} },
};

const diff = { regressed: [], improved: [], new_errors: [], resolved_errors: [] };
const radarData = { dimensions: ["math", "logic"], scores_a: [0.8, 0.7], scores_b: [0.85, 0.75] };

describe("Compare page", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    mockUseSessions.mockReturnValue({
      data: [
        { id: "s1", model_version: "v1.0", benchmark: "mmlu" },
        { id: "s2", model_version: "v2.0", benchmark: "mmlu" },
      ],
      isLoading: false,
    });

    mockUseVersionComparison.mockImplementation((versionA: string | null, versionB: string | null) => ({
      data: versionA && versionB ? comparison : null,
      isLoading: false,
    }));
    mockUseVersionDiff.mockImplementation((versionA: string | null, versionB: string | null) => ({
      data: versionA && versionB ? diff : null,
      isLoading: false,
    }));
    mockUseRadarData.mockImplementation((versionA: string | null, versionB: string | null) => ({
      data: versionA && versionB ? radarData : null,
      isLoading: false,
    }));
  });

  it("renders the selector and empty prompt before versions are chosen", () => {
    render(<Compare />);

    expect(screen.getByText("版本对比")).toBeInTheDocument();
    expect(screen.getByText("请先选择两个版本")).toBeInTheDocument();
    expect(screen.getByText("versions:v1.0,v2.0")).toBeInTheDocument();
  });

  it("shows radar and diff after selecting two versions", () => {
    render(<Compare />);

    fireEvent.click(screen.getByText("select-a"));
    fireEvent.click(screen.getByText("select-b"));
    fireEvent.click(screen.getByText("compare"));

    expect(mockUseVersionComparison).toHaveBeenLastCalledWith("v1.0", "v2.0");
    expect(mockUseVersionDiff).toHaveBeenLastCalledWith("v1.0", "v2.0");
    expect(mockUseRadarData).toHaveBeenLastCalledWith("v1.0", "v2.0");
    expect(screen.getByText("能力雷达图")).toBeInTheDocument();
    expect(screen.getByText("变化摘要")).toBeInTheDocument();
  });
});
