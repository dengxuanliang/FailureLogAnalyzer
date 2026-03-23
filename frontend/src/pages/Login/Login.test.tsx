import { jest } from "@jest/globals";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import apiClient from "@/api/client";
import "@/i18n";
import { AuthProvider } from "@/contexts/AuthContext";
import Login from "./index";

const makeToken = (payload: Record<string, unknown>) => {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
};

const renderLogin = () =>
  render(
    <MemoryRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      initialEntries={["/login"]}
    >
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/overview" element={<div>Overview Page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );

describe("Login page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it("renders login form", () => {
    renderLogin();
    expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("shows error on failed login", async () => {
    jest.spyOn(apiClient, "post").mockRejectedValueOnce(new Error("Unauthorized"));

    renderLogin();

    await userEvent.type(screen.getByLabelText("Username"), "bad");
    await userEvent.type(screen.getByLabelText("Password"), "bad");
    await userEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByText("Invalid username or password")).toBeInTheDocument();
    });
    expect(screen.queryByText("Overview Page")).not.toBeInTheDocument();
  });

  it("navigates to overview after successful login", async () => {
    jest.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        access_token: makeToken({
          sub: "user-1",
          role: "analyst",
          exp: Math.floor(Date.now() / 1000) + 3600,
        }),
      },
    } as Awaited<ReturnType<typeof apiClient.post>>);

    renderLogin();

    await userEvent.type(screen.getByLabelText("Username"), "good");
    await userEvent.type(screen.getByLabelText("Password"), "good");
    await userEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByText("Overview Page")).toBeInTheDocument();
    });
    expect(localStorage.getItem("token")).not.toBeNull();
  });

  it("redirects to overview when a valid token already exists", async () => {
    localStorage.setItem(
      "token",
      makeToken({
        sub: "user-1",
        role: "analyst",
        exp: Math.floor(Date.now() / 1000) + 3600,
      }),
    );

    renderLogin();

    await waitFor(() => {
      expect(screen.getByText("Overview Page")).toBeInTheDocument();
    });
  });
});
