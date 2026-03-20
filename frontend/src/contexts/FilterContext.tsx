import { createContext, useCallback, useMemo, type PropsWithChildren } from "react";
import { useSearchParams } from "react-router-dom";
import type { GlobalFilters } from "../types/api";

export type FilterKey = keyof GlobalFilters;

export interface FilterContextValue extends GlobalFilters {
  setFilter: (key: FilterKey, value: string | null) => void;
  resetFilters: () => void;
}

const filterKeys: FilterKey[] = [
  "benchmark",
  "model_version",
  "time_range_start",
  "time_range_end",
];

export const FilterContext = createContext<FilterContextValue | null>(null);

function getFilterValue(searchParams: URLSearchParams, key: FilterKey): string | null {
  const value = searchParams.get(key);
  return value === null || value === "" ? null : value;
}

function readFilters(searchParams: URLSearchParams): GlobalFilters {
  return {
    benchmark: getFilterValue(searchParams, "benchmark"),
    model_version: getFilterValue(searchParams, "model_version"),
    time_range_start: getFilterValue(searchParams, "time_range_start"),
    time_range_end: getFilterValue(searchParams, "time_range_end"),
  };
}

export function FilterProvider({ children }: PropsWithChildren) {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => readFilters(searchParams), [searchParams]);

  const setFilter = useCallback(
    (key: FilterKey, value: string | null) => {
      setSearchParams(
        (currentSearchParams) => {
          const nextSearchParams = new URLSearchParams(currentSearchParams);

          if (value === null || value === "") {
            nextSearchParams.delete(key);
          } else {
            nextSearchParams.set(key, value);
          }

          return nextSearchParams;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const resetFilters = useCallback(() => {
    setSearchParams(
      (currentSearchParams) => {
        const nextSearchParams = new URLSearchParams(currentSearchParams);

        filterKeys.forEach((key) => {
          nextSearchParams.delete(key);
        });

        return nextSearchParams;
      },
      { replace: true }
    );
  }, [setSearchParams]);

  const value = useMemo<FilterContextValue>(
    () => ({
      ...filters,
      setFilter,
      resetFilters,
    }),
    [filters, resetFilters, setFilter]
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}
