// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useIsPortrait } from "../useIsPortrait";

type ChangeHandler = (e: MediaQueryListEvent) => void;

const makeMql = (matches: boolean) => {
  const listeners: ChangeHandler[] = [];
  return {
    matches,
    addEventListener: vi.fn((_: string, fn: ChangeHandler) =>
      listeners.push(fn),
    ),
    removeEventListener: vi.fn((_: string, fn: ChangeHandler) => {
      const i = listeners.indexOf(fn);
      if (i !== -1) listeners.splice(i, 1);
    }),
    _fire: (newMatches: boolean) => {
      listeners.forEach((fn) =>
        fn({ matches: newMatches } as MediaQueryListEvent),
      );
    },
  };
};

let mql: ReturnType<typeof makeMql>;

const setMql = (matches: boolean) => {
  mql = makeMql(matches);
  Object.defineProperty(window, "matchMedia", {
    value: vi.fn().mockReturnValue(mql),
    writable: true,
    configurable: true,
  });
};

describe("useIsPortrait", () => {
  beforeEach(() => {
    setMql(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns false when initial orientation is landscape", () => {
    setMql(false);
    const { result } = renderHook(() => useIsPortrait());
    expect(result.current).toBe(false);
  });

  it("returns true when initial orientation is portrait", () => {
    setMql(true);
    const { result } = renderHook(() => useIsPortrait());
    expect(result.current).toBe(true);
  });

  it("updates to true when orientation changes to portrait", () => {
    setMql(false);
    const { result } = renderHook(() => useIsPortrait());
    expect(result.current).toBe(false);
    act(() => {
      mql._fire(true);
    });
    expect(result.current).toBe(true);
  });

  it("updates to false when orientation changes back to landscape", () => {
    setMql(true);
    const { result } = renderHook(() => useIsPortrait());
    act(() => {
      mql._fire(false);
    });
    expect(result.current).toBe(false);
  });

  it("registers an event listener on mount", () => {
    setMql(false);
    renderHook(() => useIsPortrait());
    expect(mql.addEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function),
    );
  });

  it("removes the event listener on unmount", () => {
    setMql(false);
    const { unmount } = renderHook(() => useIsPortrait());
    unmount();
    expect(mql.removeEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function),
    );
  });

  it("does not update state after unmount", () => {
    setMql(false);
    const { result, unmount } = renderHook(() => useIsPortrait());
    unmount();
    act(() => {
      mql._fire(true);
    });
    expect(result.current).toBe(false);
  });
});
