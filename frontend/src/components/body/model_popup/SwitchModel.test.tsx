// src/components/body/model_popup/SwitchModel.test.tsx
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import SwitchModel from "./ModelPopup";
import testData from "../../../static_data/static_model_data.json";
import { useModalStore } from "@stores/useModalStore";
import { useModelStore } from "@stores/useModelStore";

// Mock the stores
vi.mock("@stores/useModalStore");
vi.mock("@stores/useModelStore");

describe("SwitchModel Component", () => {
  let mockSetSelectedModel: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockSetSelectedModel = vi.fn();

    // Setup modal store mock
    vi.mocked(useModalStore).mockReturnValue({
      closeModelInfoPopup: vi.fn(),
      // Add other required store properties as needed
    } as any);

    // Setup model store mock
    vi.mocked(useModelStore).mockReturnValue({
      selectedModel: "",
      metadata: [],
      isLoading: false,
      setSelectedModel: mockSetSelectedModel,
      setMetadata: vi.fn(),
      setLoading: vi.fn(),
    });
  });

  it("populates the grid with test data", async () => {
    // Render the component
    render(<SwitchModel />);

    // Check if the model names from testData are displayed
    testData.forEach((data) => {
      expect(screen.getByText(data.model_name)).toBeInTheDocument();
    });

    // Simulate model selection
    const modelToSelect = testData[0].pipeline_id;
    const modelName = testData[0].model_name;
    fireEvent.click(screen.getByText(modelName));

    // Assert setSelectedModel was called with the pipeline_id (not model name)
    expect(mockSetSelectedModel).toHaveBeenCalledWith(modelToSelect);
  });
});
