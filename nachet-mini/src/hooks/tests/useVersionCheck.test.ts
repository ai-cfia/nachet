// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { isRemoteVersionNewer } from "../useVersionCheck";

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
