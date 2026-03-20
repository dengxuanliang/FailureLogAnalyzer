import { useContext } from "react";
import { FilterContext } from "../contexts/FilterContext";

export function useGlobalFilters() {
  const context = useContext(FilterContext);

  if (context === null) {
    throw new Error("useGlobalFilters must be used within a FilterProvider");
  }

  return context;
}
