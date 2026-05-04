// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { versions } from "../../_versions";
import { isRemoteVersionNewer, useVersionCheck } from "../useVersionCheck";

describe("isRemoteVersionNewer", () => {
  it("returns true when the remote semver is greater than the current version", () => {
    expect(isRemoteVersionNewer("0.10.1", "0.10.0")).toBe(true);
    expect(isRemoteVersionNewer("0.11.0", "0.10.9")).toBe(true);
    expect(isRemoteVersionNewer("1.0.0", "0.99.99")).toBe(true);
  });

  it("returns false when the remote semver is equal to or older than the current version", () => {
    expect(isRemoteVersionNewer("0.10.0", "0.10.0")).toBe(false);
    expect(isRemoteVersionNewer("0.9.6", "0.10.0")).toBe(false);
    expect(isRemoteVersionNewer("0.10.0", "0.10.1")).toBe(false);
  });

  it("handles v-prefixed versions and prerelease ordering", () => {
    expect(isRemoteVersionNewer("v0.10.1", "0.10.0")).toBe(true);
    expect(isRemoteVersionNewer("0.10.0", "0.10.0-beta.1")).toBe(true);
    expect(isRemoteVersionNewer("0.10.0-beta.1", "0.10.0")).toBe(false);
    expect(isRemoteVersionNewer("0.10.0-beta.10", "0.10.0-beta.2")).toBe(true);
    expect(isRemoteVersionNewer("0.10.0+20260504", "0.10.0")).toBe(false);
  });
});

describe("useVersionCheck", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        text: () =>
          Promise.resolve(`export const versions = { version: "9.9.9" };`),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("opens the dialog and stores the remote version when a newer version exists", async () => {
    const { result } = renderHook(() => useVersionCheck());

    await waitFor(() => expect(result.current.dialogOpen).toBe(true));

    expect(result.current.remoteVersion).toBe("9.9.9");
  });

  it("does not open the dialog when the remote version matches the current version", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      text: () =>
        Promise.resolve(
          `export const versions = { version: "${versions.version}" };`,
        ),
    } as Response);

    const { result } = renderHook(() => useVersionCheck());

    await waitFor(() => expect(fetch).toHaveBeenCalledOnce());

    expect(result.current.dialogOpen).toBe(false);
    expect(result.current.remoteVersion).toBeNull();
  });

  it("closes the dialog without clearing the remote version", async () => {
    const { result } = renderHook(() => useVersionCheck());

    await waitFor(() => expect(result.current.dialogOpen).toBe(true));

    act(() => result.current.closeDialog());

    expect(result.current.dialogOpen).toBe(false);
    expect(result.current.remoteVersion).toBe("9.9.9");
  });
});
