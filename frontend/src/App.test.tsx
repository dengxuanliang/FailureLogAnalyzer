import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";

const mockRouter = { future: {}, state: {} };

jest.unstable_mockModule("react-router-dom", () => ({
  RouterProvider: ({ router }: { router: unknown }) => (
    <div data-testid="router-provider">{String(router === mockRouter)}</div>
  ),
}));

jest.unstable_mockModule("@/router", () => ({
  router: mockRouter,
}));

const { default: App } = await import("./App");

test("renders the app with the configured router", () => {
  render(<App />);

  expect(screen.getByTestId("router-provider")).toHaveTextContent("true");
});
