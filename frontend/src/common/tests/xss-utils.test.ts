import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { validateUserInput } from "../xss-utils";
import { validateApiResponse } from "../validation";

beforeEach(() =>
  vi.spyOn(console, "error").mockImplementation(() => undefined),
);
afterEach(() => vi.restoreAllMocks());

describe("Validation error causes", () => {
  it.each([
    ["text", "Invalid text input"],
    ["userInput", "Unsafe user input detected"],
    ["url", "Invalid or unsafe URL"],
  ] as const)("preserves the cause and message for %s", (method, message) => {
    expect(() =>
      validateUserInput[method](null as unknown as string),
    ).toThrowError(
      expect.objectContaining({ message, cause: expect.any(z.ZodError) }),
    );
  });

  it("preserves the API validation error without changing its message prefix", () => {
    expect(() => validateApiResponse(z.string(), 123, "test API")).toThrowError(
      expect.objectContaining({
        message: expect.stringContaining("Invalid API response from test API:"),
        cause: expect.any(z.ZodError),
      }),
    );
  });

  it("keeps successful validation unchanged", () => {
    expect(validateUserInput.text("hello")).toBe("hello");
    expect(validateApiResponse(z.string(), "hello", "test API")).toBe("hello");
  });
});
