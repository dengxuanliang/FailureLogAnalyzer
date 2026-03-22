/* eslint-env jest, browser */

import { jest } from "@jest/globals";
import type { AxiosError, AxiosRequestConfig } from "axios";
import * as clientModule from "./client";

const { default: apiClient } = clientModule;

const getRequestHandler = () => {
  const { handlers } = (apiClient.interceptors.request as unknown as {
    handlers: Array<{ fulfilled: (config: AxiosRequestConfig) => AxiosRequestConfig }>;
  });

  return handlers[0].fulfilled;
};

const getResponseErrorHandler = () => {
  const { handlers } = (apiClient.interceptors.response as unknown as {
    handlers: Array<{ rejected: (error: AxiosError) => Promise<never> }>;
  });

  return handlers[0].rejected;
};

describe("apiClient interceptors", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("adds an Authorization header when a token is stored", () => {
    localStorage.setItem("token", "token-value");

    const handler = getRequestHandler();
    const result = handler({} as AxiosRequestConfig);

    expect(result.headers?.Authorization).toBe("Bearer token-value");
  });

  it("clears the token and redirects on a 401 response", async () => {
    localStorage.setItem("token", "token-value");

    const error = {
      response: {
        status: 401,
        data: { message: "Session expired" },
      },
      config: {},
      isAxiosError: true,
      name: "AxiosError",
      message: "Request failed with status code 401",
      toJSON: () => ({}),
    } as AxiosError;

    const assignSpy = jest.spyOn(clientModule.navigation, "assign").mockImplementation(() => {});
    const handler = getResponseErrorHandler();

    await expect(handler(error)).rejects.toBe(error);

    expect(localStorage.getItem("token")).toBeNull();
    expect(assignSpy).toHaveBeenCalledWith("/login");
    assignSpy.mockRestore();
  });

  it("maps non-401 axios errors to ApiError with status, message, detail", async () => {
    const responseData = {
      message: "Server failure",
      detail: "Detailed failure",
    };

    const error = {
      response: {
        status: 500,
        data: responseData,
      },
      config: {},
      isAxiosError: true,
      name: "AxiosError",
      message: "Request failed with status code 500",
      toJSON: () => ({}),
    } as AxiosError;

    const handler = getResponseErrorHandler();

    await expect(handler(error)).rejects.toMatchObject({
      status: 500,
      message: "Detailed failure",
      detail: responseData,
    });
  });
});
