import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { FilterProvider } from "./FilterContext";
import { useGlobalFilters } from "../hooks/useGlobalFilters";

function FilterProbe() {
  const filters = useGlobalFilters();
  const location = useLocation();

  return (
    <>
      <div data-testid="benchmark">{filters.benchmark ?? "null"}</div>
      <div data-testid="model-version">{filters.model_version ?? "null"}</div>
      <div data-testid="time-range-start">{filters.time_range_start ?? "null"}</div>
      <div data-testid="time-range-end">{filters.time_range_end ?? "null"}</div>
      <div data-testid="search">{location.search}</div>
      <button type="button" onClick={() => filters.setFilter("benchmark", "ceval")}>set benchmark</button>
      <button type="button" onClick={() => filters.setFilter("model_version", null)}>clear model version</button>
      <button type="button" onClick={() => filters.resetFilters()}>reset filters</button>
    </>
  );
}

describe("FilterProvider", () => {
  it("initializes global filters from URL query params", () => {
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={[
          "/?benchmark=mmlu&model_version=gpt-4.1&time_range_start=2026-01-01&time_range_end=2026-01-31",
        ]}
      >
        <FilterProvider>
          <FilterProbe />
        </FilterProvider>
      </MemoryRouter>
    );

    expect(screen.getByTestId("benchmark")).toHaveTextContent("mmlu");
    expect(screen.getByTestId("model-version")).toHaveTextContent("gpt-4.1");
    expect(screen.getByTestId("time-range-start")).toHaveTextContent("2026-01-01");
    expect(screen.getByTestId("time-range-end")).toHaveTextContent("2026-01-31");
  });

  it("updates and resets filters while syncing managed query params", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/?tab=overview&model_version=gpt-4.1"]}
      >
        <FilterProvider>
          <FilterProbe />
        </FilterProvider>
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: "set benchmark" }));

    expect(screen.getByTestId("benchmark")).toHaveTextContent("ceval");
    expect(new URLSearchParams(screen.getByTestId("search").textContent ?? "").get("benchmark")).toBe("ceval");
    expect(new URLSearchParams(screen.getByTestId("search").textContent ?? "").get("tab")).toBe("overview");

    await user.click(screen.getByRole("button", { name: "clear model version" }));

    expect(screen.getByTestId("model-version")).toHaveTextContent("null");
    expect(new URLSearchParams(screen.getByTestId("search").textContent ?? "").get("model_version")).toBeNull();

    await user.click(screen.getByRole("button", { name: "reset filters" }));

    expect(screen.getByTestId("benchmark")).toHaveTextContent("null");
    expect(screen.getByTestId("model-version")).toHaveTextContent("null");
    expect(screen.getByTestId("time-range-start")).toHaveTextContent("null");
    expect(screen.getByTestId("time-range-end")).toHaveTextContent("null");

    const searchParams = new URLSearchParams(screen.getByTestId("search").textContent ?? "");
    expect(searchParams.get("tab")).toBe("overview");
    expect(searchParams.get("benchmark")).toBeNull();
    expect(searchParams.get("model_version")).toBeNull();
    expect(searchParams.get("time_range_start")).toBeNull();
    expect(searchParams.get("time_range_end")).toBeNull();
  });
});
