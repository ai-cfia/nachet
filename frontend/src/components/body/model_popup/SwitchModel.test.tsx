// src/components/body/model_popup/SwitchModel.test.tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import SwitchModel from "./index";
import testData from "../../../static_data/static_model_data.json";

describe("SwitchModel Component", () => {
  it("populates the grid with test data", async () => {
    // Mock the props
    const mockSetSwitchModelOpen = vi.fn();
    const mockSetSelectedModel = vi.fn();

    // Render the component with test data
    render(
      <SwitchModel
        setSwitchModelOpen={mockSetSwitchModelOpen}
        switchModelOpen={true}
        selectedModel=""
        setSelectedModel={mockSetSelectedModel}
        realData={[]} // Since we're testing, realData will not be used
      />,
    );

    // Check if the model names from testData are displayed
    testData.forEach((data) => {
      expect(screen.getByText(data.model_name)).toBeInTheDocument();
    });

    // Simulate model selection
    const modelToSelect = testData[0].model_name;
    fireEvent.click(screen.getByText(modelToSelect));

    // Assert setSelectedModel was called with the selected model name
    expect(mockSetSelectedModel).toHaveBeenCalledWith(modelToSelect);
  });
});
