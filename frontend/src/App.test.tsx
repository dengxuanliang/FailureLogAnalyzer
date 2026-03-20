import { render, screen } from "@testing-library/react";
import App from "./App";

test("renders the FailureLogAnalyzer label", () => {
  render(<App />);
  expect(screen.getByText("FailureLogAnalyzer")).toBeInTheDocument();
});
