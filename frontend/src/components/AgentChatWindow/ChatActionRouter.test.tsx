import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { FilterContext, type FilterContextValue } from "@/contexts/FilterContext";
import { ChatActionRouter } from "./ChatActionRouter";

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

describe("ChatActionRouter", () => {
  it("navigate action updates the route", () => {
    const filterValue: FilterContextValue = {
      benchmark: null,
      model_version: null,
      time_range_start: null,
      time_range_end: null,
      setFilter: jest.fn(),
      resetFilters: jest.fn(),
    };

    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/overview"]}
      >
        <FilterContext.Provider value={filterValue}>
          <ChatActionRouter action={{ type: "navigate", page: "compare" }} />
          <LocationProbe />
        </FilterContext.Provider>
      </MemoryRouter>,
    );

    expect(screen.getByTestId("location")).toHaveTextContent("/compare");
  });

  it("set_filter action calls setFilter with the given key and value", () => {
    const setFilter = jest.fn();
    const filterValue: FilterContextValue = {
      benchmark: null,
      model_version: null,
      time_range_start: null,
      time_range_end: null,
      setFilter,
      resetFilters: jest.fn(),
    };

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <FilterContext.Provider value={filterValue}>
          <ChatActionRouter action={{ type: "set_filter", key: "benchmark", value: "mmlu" }} />
        </FilterContext.Provider>
      </MemoryRouter>,
    );

    expect(setFilter).toHaveBeenCalledWith("benchmark", "mmlu");
  });

  it("null action renders nothing", () => {
    const filterValue: FilterContextValue = {
      benchmark: null,
      model_version: null,
      time_range_start: null,
      time_range_end: null,
      setFilter: jest.fn(),
      resetFilters: jest.fn(),
    };

    const { container } = render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <FilterContext.Provider value={filterValue}>
          <ChatActionRouter action={null} />
        </FilterContext.Provider>
      </MemoryRouter>,
    );

    expect(container.firstChild).toBeNull();
  });
});
