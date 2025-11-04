/**
 * Shared test utilities for Zustand store testing
 */

import { act } from "@testing-library/react";
import { StoreApi, UseBoundStore } from "zustand";

/**
 * Helper to reset a Zustand store to its initial state
 * Useful for ensuring test isolation
 */
export const resetStore = <T>(store: UseBoundStore<StoreApi<T>>) => {
  // Get the initial state by creating a fresh instance
  const initialState = store.getState();
  act(() => {
    store.setState(initialState, true); // true = replace entire state
  });
};

/**
 * Helper to get a snapshot of current store state
 */
export const getStoreSnapshot = <T>(store: UseBoundStore<StoreApi<T>>): T => {
  return { ...store.getState() };
};

/**
 * Helper to wait for async state updates
 */
export const waitForStoreUpdate = async (
  callback: () => void,
  delay = 0,
): Promise<void> => {
  await act(async () => {
    callback();
    if (delay > 0) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  });
};

/**
 * Mock file generator for upload testing
 */
export const createMockFile = (
  name = "test.jpg",
  size = 1024,
  type = "image/jpeg",
): File => {
  const blob = new Blob(["x".repeat(size)], { type });
  return new File([blob], name, { type });
};

/**
 * Mock image data for testing
 */
export const createMockImageData = (overrides = {}) => ({
  index: 0,
  src: "data:image/png;base64,test",
  imageName: "test-image.jpg",
  imageDescription: "",
  imageDims: [800, 600],
  workflowIds: [],
  activeWorkflowId: null,
  ...overrides,
});

/**
 * Assert that two Maps have the same content
 * Returns boolean for use with expect() in tests
 */
export const mapsAreEqual = <K, V>(
  map1: Map<K, V>,
  map2: Map<K, V>,
): boolean => {
  if (map1.size !== map2.size) return false;
  for (const [key, value] of map1) {
    if (!map2.has(key)) return false;
    const val2 = map2.get(key);
    if (JSON.stringify(value) !== JSON.stringify(val2)) return false;
  }
  return true;
};

/**
 * Check if a Map contains a key-value pair
 */
export const mapContains = <K, V>(
  map: Map<K, V>,
  key: K,
  expectedValue: Partial<V>,
): boolean => {
  if (!map.has(key)) return false;
  const value = map.get(key);
  if (!value) return false;

  // Check if all properties in expectedValue match
  for (const [k, v] of Object.entries(expectedValue)) {
    if ((value as Record<string, unknown>)[k] !== v) return false;
  }
  return true;
};

/**
 * Create mock API inference data for testing
 */
export const createMockApiInferenceData = (overrides = {}) => ({
  filename: "test-image.jpg",
  imageId: "image-123",
  inferenceId: "inf-123",
  totalBoxes: 0,
  labelOccurrence: {},
  models: [{ name: "Test Model", version: "1.0" }],
  boxes: [],
  ...overrides,
});
