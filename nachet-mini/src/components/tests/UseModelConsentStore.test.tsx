import { act, renderHook } from "@testing-library/react";
import { useModelLoadConsentStore } from "@stores/useModelLoadConsentStore";
import { beforeEach, describe, it, expect } from "vitest";

beforeEach(() => {
  useModelLoadConsentStore.setState({
    hasAcknowledgedModelLoadWarning: false,
    pendingInferenceRequest: null,
  });
  localStorage.clear();
});

describe("useModelLoadConsentStore", () => {
  it("starts with warning not acknowledged", () => {
    const { result } = renderHook(() => useModelLoadConsentStore());
    expect(result.current.hasAcknowledgedModelLoadWarning).toBe(false);
  });

  it("acknowledgeModelLoadWarning sets the flag to true", () => {
    const { result } = renderHook(() => useModelLoadConsentStore());
    act(() => result.current.acknowledgeModelLoadWarning());
    expect(result.current.hasAcknowledgedModelLoadWarning).toBe(true);
  });

  it("persists acknowledgement to localStorage", () => {
    const { result } = renderHook(() => useModelLoadConsentStore());
    act(() => result.current.acknowledgeModelLoadWarning());
    const stored = JSON.parse(
      localStorage.getItem("nachet-mini-model-load-consent") ?? "{}",
    );
    expect(stored.state.hasAcknowledgedModelLoadWarning).toBe(true);
  });

  it("does not persist pendingInferenceRequest", () => {
    const { result } = renderHook(() => useModelLoadConsentStore());
    act(() =>
      result.current.setPendingInferenceRequest({
        imageSrc: "data:image/png;base64,abc",
        imageIndex: 0,
      }),
    );
    const stored = JSON.parse(
      localStorage.getItem("nachet-mini-model-load-consent") ?? "{}",
    );
    expect(stored.state.pendingInferenceRequest).toBeUndefined();
  });

  it("setPendingInferenceRequest stores and clears the request", () => {
    const { result } = renderHook(() => useModelLoadConsentStore());
    const req = { imageSrc: "data:image/png;base64,abc", imageIndex: 1 };
    act(() => result.current.setPendingInferenceRequest(req));
    expect(result.current.pendingInferenceRequest).toEqual(req);
    act(() => result.current.setPendingInferenceRequest(null));
    expect(result.current.pendingInferenceRequest).toBeNull();
  });
});