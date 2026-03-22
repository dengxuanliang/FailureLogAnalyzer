import { jest } from "@jest/globals";

export const ensureMatchMedia = () => {
  Object.defineProperty(window, "getComputedStyle", {
    writable: true,
    value: () => ({
      getPropertyValue: () => "",
    }),
  });

  if ("matchMedia" in window && typeof window.matchMedia === "function") {
    return;
  }

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
};
