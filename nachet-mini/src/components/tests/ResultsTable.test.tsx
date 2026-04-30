import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import frMain from "../../locales/fr/main";
import type { InferenceResult } from "@common/types";
import ResultsTable from "../ResultsTable";

const makeResult = (
  overrides: Partial<InferenceResult> = {},
): InferenceResult => ({
  scores: [],
  classifications: [],
  boxes: [],
  topN: [],
  overlapping: [],
  overlappingIndices: [],
  labelOccurrence: {},
  totalBoxes: 0,
  models: [],
  completedAt: "",
  isActive: false,
  minBoxSize: 10,
  ...overrides,
});

const renderTable = (
  result: InferenceResult | null,
  switchTable: boolean,
  onSwitchTableChange = vi.fn(),
) =>
  render(
    <I18nextProvider i18n={i18n}>
      <ResultsTable
        result={result}
        switchTable={switchTable}
        onSwitchTableChange={onSwitchTableChange}
      />
    </I18nextProvider>,
  );

const makeClassificationResult = (
  classifications: string[],
  scores: number[],
  topN: InferenceResult["topN"] = classifications.map(() => []),
  overrides: Partial<InferenceResult> = {},
) =>
  makeResult({
    classifications,
    scores,
    topN,
    ...overrides,
  });

describe("ResultsTable", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  afterEach(cleanup);

  describe("structure", () => {
    it("renders the component root", async () => {
      renderTable(null, false);
      await expect
        .element(page.getByTestId("results-table-component"))
        .toBeVisible();
    });

    it("renders the title", async () => {
      renderTable(null, false);
      await expect
        .element(page.getByText(enMain.resultsTable.title))
        .toBeVisible();
    });

    it("renders the switch table button with correct aria-label", async () => {
      renderTable(null, false);
      await expect
        .element(page.getByRole("button", { name: "switch table view" }))
        .toBeVisible();
    });

    it("switch table button is disabled", async () => {
      renderTable(null, false);
      await expect
        .element(page.getByRole("button", { name: "switch table view" }))
        .toBeDisabled();
    });

    it("does not call onSwitchTableChange when the disabled button is clicked", async () => {
      const onSwitchTableChange = vi.fn();
      const { getByRole } = renderTable(null, false, onSwitchTableChange);
      fireEvent.click(getByRole("button", { name: "switch table view" }));
      expect(onSwitchTableChange).not.toHaveBeenCalled();
    });
  });

  describe("with null result", () => {
    it("renders no table rows when result is null", async () => {
      renderTable(null, false);
      expect(await page.getByRole("row").all()).toHaveLength(0);
    });

    it("renders no table rows in switchTable mode when result is null", async () => {
      renderTable(null, true);
      expect(await page.getByRole("row").all()).toHaveLength(0);
    });
  });

  describe("label occurrence mode (switchTable=true)", () => {
    const result = makeResult({
      labelOccurrence: { Wheat: 3, "Canary Grass": 5 },
    });

    it("renders a row for each label", async () => {
      renderTable(result, true);
      expect(await page.getByRole("row").all()).toHaveLength(2);
    });

    it("renders label names in the table", async () => {
      renderTable(result, true);
      await expect.element(page.getByText("Wheat")).toBeVisible();
      await expect.element(page.getByText("Canary Grass")).toBeVisible();
    });

    it("renders label occurrence counts", async () => {
      renderTable(result, true);
      await expect.element(page.getByText("3")).toBeVisible();
      await expect.element(page.getByText("5")).toBeVisible();
    });

    it("does not render classification rows when switchTable is true", async () => {
      const resultWithBoth = makeResult({
        labelOccurrence: { Wheat: 2 },
        classifications: ["Wheat", "Wheat"],
        scores: [0.9, 0.8],
        topN: [[], []],
      });
      renderTable(resultWithBoth, true);
      // Only label occurrence rows (1), no classification rows
      expect(await page.getByRole("row").all()).toHaveLength(1);
      expect(await page.getByText("90%").all()).toHaveLength(0);
    });

    it("marks a label row selected when its label cell is clicked", async () => {
      const user = userEvent.setup();
      const { getByText } = renderTable(result, true);
      const wheatRow = getByText("Wheat").closest("tr");

      expect(wheatRow).toHaveAttribute("aria-selected", "false");
      await user.click(getByText("Wheat"));
      expect(wheatRow).toHaveAttribute("aria-selected", "true");
    });

    it("deselects the label when the same label is clicked again", async () => {
      const user = userEvent.setup();
      const { getByText } = renderTable(result, true);
      const wheatRow = getByText("Wheat").closest("tr");

      await user.click(getByText("Wheat"));
      expect(wheatRow).toHaveAttribute("aria-selected", "true");
      await user.click(getByText("Wheat"));
      expect(wheatRow).toHaveAttribute("aria-selected", "false");
    });
  });

  describe("classification mode (switchTable=false)", () => {
    it("renders a row per classification", async () => {
      const result = makeClassificationResult(
        ["Wheat", "Canary Grass"],
        [0.9, 0.75],
      );
      renderTable(result, false);
      expect(await page.getByRole("row").all()).toHaveLength(2);
    });

    it("renders prediction labels in the table", async () => {
      const result = makeClassificationResult(
        ["Wheat", "Canary Grass"],
        [0.9, 0.75],
      );
      renderTable(result, false);
      await expect.element(page.getByText("Wheat")).toBeVisible();
      await expect.element(page.getByText("Canary Grass")).toBeVisible();
    });

    it("renders score as rounded percentage", async () => {
      const result = makeClassificationResult(["Wheat"], [0.876]);
      renderTable(result, false);
      await expect.element(page.getByText("88%")).toBeVisible();
    });

    it("uses topN[0].score instead of scores when topN is available", async () => {
      const result = makeResult({
        classifications: ["Wheat"],
        scores: [0.5],
        topN: [[{ score: 0.92, label: "Wheat" }]],
      });
      renderTable(result, false);
      await expect.element(page.getByText("92%")).toBeVisible();
    });

    it("shows a spinner for classifying rows (empty prediction)", async () => {
      const result = makeResult({
        classifications: [""],
        scores: [0],
        topN: [[]],
      });
      renderTable(result, false);
      await expect.element(page.getByRole("progressbar")).toBeVisible();
    });

    it("shows 'Classifying...' text for empty predictions", async () => {
      const result = makeResult({
        classifications: [""],
        scores: [0],
        topN: [[]],
      });
      renderTable(result, false);
      await expect
        .element(page.getByText(enMain.resultsTable.classifying))
        .toBeVisible();
    });

    it("shows '...' instead of a score for classifying rows", async () => {
      const result = makeResult({
        classifications: [""],
        scores: [0],
        topN: [[]],
      });
      renderTable(result, false);
      await expect
        .element(page.getByText("...", { exact: true }))
        .toBeVisible();
    });

    it("does not render label occurrence rows when switchTable is false", async () => {
      const result = makeResult({
        classifications: ["Wheat"],
        scores: [0.9],
        topN: [[]],
        labelOccurrence: { Wheat: 1 },
      });
      renderTable(result, false);
      // Should show 1 classification row, not 2 (no label occurrence row)
      expect(await page.getByRole("row").all()).toHaveLength(1);
    });
  });

  describe("row expansion", () => {
    const topNData = [
      { score: 0.9, label: "Wheat" },
      { score: 0.07, label: "Rye" },
    ];
    const result = makeResult({
      classifications: ["Wheat"],
      scores: [0.9],
      topN: [topNData],
    });

    it("does not show topN details before clicking a row", async () => {
      renderTable(result, false);
      expect(
        await page.getByText(enMain.resultsTable.topResults).all(),
      ).toHaveLength(0);
    });

    it("expands a row to show top results on click", async () => {
      const user = userEvent.setup();
      const { getAllByRole } = renderTable(result, false);
      await user.click(getAllByRole("row")[0]);
      await expect
        .element(page.getByText(enMain.resultsTable.topResults))
        .toBeVisible();
    });

    it("shows topN labels and scores in the expanded row", async () => {
      const user = userEvent.setup();
      const { getAllByRole } = renderTable(result, false);
      await user.click(getAllByRole("row")[0]);
      await expect.element(page.getByText(/Wheat: 90.00%/)).toBeVisible();
      await expect.element(page.getByText(/Rye: 7.00%/)).toBeVisible();
    });

    it("collapses an expanded row on second click", async () => {
      const user = userEvent.setup();
      const { getAllByRole } = renderTable(result, false);
      await user.click(getAllByRole("row")[0]);
      await expect
        .element(page.getByText(enMain.resultsTable.topResults))
        .toBeVisible();
      await user.click(getAllByRole("row")[0]);
      expect(
        await page.getByText(enMain.resultsTable.topResults).all(),
      ).toHaveLength(0);
    });

    it("switches expansion to the newly clicked row", async () => {
      const user = userEvent.setup();
      const resultWithTwoExpandableRows = makeClassificationResult(
        ["Wheat", "Rye"],
        [0.9, 0.8],
        [
          [{ score: 0.9, label: "Wheat top" }],
          [{ score: 0.8, label: "Rye top" }],
        ],
      );
      const { getAllByRole, getByText } = renderTable(
        resultWithTwoExpandableRows,
        false,
      );

      await user.click(getAllByRole("row")[0]);
      await expect.element(page.getByText(/Wheat top: 90\.00%/)).toBeVisible();

      await user.click(getByText("Rye"));
      expect(await page.getByText(/Wheat top: 90\.00%/).all()).toHaveLength(0);
      await expect.element(page.getByText(/Rye top: 80\.00%/)).toBeVisible();
    });

    it("does not expand a classifying row when clicked", async () => {
      const user = userEvent.setup();
      const classifyingResult = makeClassificationResult([""], [0]);
      const { getAllByRole } = renderTable(classifyingResult, false);
      await user.click(getAllByRole("row")[0]);
      expect(
        await page.getByText(enMain.resultsTable.topResults).all(),
      ).toHaveLength(0);
    });

    it("does not expand a row that has no top results", async () => {
      const user = userEvent.setup();
      const resultWithoutTopN = makeClassificationResult(["Wheat"], [0.9]);
      const { getAllByRole } = renderTable(resultWithoutTopN, false);

      await user.click(getAllByRole("row")[0]);
      expect(
        await page.getByText(enMain.resultsTable.topResults).all(),
      ).toHaveLength(0);
    });
  });

  describe("score formatting in top results", () => {
    it("formats a very small positive score as '< 0.01%'", async () => {
      const result = makeResult({
        classifications: ["Wheat"],
        scores: [0.9],
        topN: [[{ score: 0.000005, label: "Rye" }]],
      });
      const user = userEvent.setup();
      const { getAllByRole } = renderTable(result, false);
      await user.click(getAllByRole("row")[0]);
      await expect.element(page.getByText(/Rye: < 0\.01%/)).toBeVisible();
    });

    it("formats a score of exactly 0.0001 normally (not as < 0.01%)", async () => {
      const result = makeResult({
        classifications: ["Wheat"],
        scores: [0.9],
        topN: [[{ score: 0.0001, label: "Rye" }]],
      });
      const user = userEvent.setup();
      const { getAllByRole } = renderTable(result, false);
      await user.click(getAllByRole("row")[0]);
      await expect.element(page.getByText(/Rye: 0\.01%/)).toBeVisible();
    });

    it("formats a score of 0 as '0.00%' (not < 0.01%)", async () => {
      const result = makeResult({
        classifications: ["Wheat"],
        scores: [0.9],
        topN: [[{ score: 0, label: "Rye" }]],
      });
      const user = userEvent.setup();
      const { getAllByRole } = renderTable(result, false);
      await user.click(getAllByRole("row")[0]);
      await expect.element(page.getByText(/Rye: 0\.00%/)).toBeVisible();
    });

    it("formats a normal score with two decimal places", async () => {
      const result = makeResult({
        classifications: ["Wheat"],
        scores: [0.9],
        topN: [[{ score: 0.5678, label: "Canary Grass" }]],
      });
      const user = userEvent.setup();
      const { getAllByRole } = renderTable(result, false);
      await user.click(getAllByRole("row")[0]);
      await expect
        .element(page.getByText(/Canary Grass: 56\.78%/))
        .toBeVisible();
    });
  });

  describe("label filtering across modes", () => {
    const result = makeResult({
      classifications: ["Wheat", "Rye", ""],
      scores: [0.9, 0.8, 0],
      topN: [[], [], []],
      labelOccurrence: { Wheat: 1, Rye: 1 },
    });

    it("shows all classification rows when no label is selected", async () => {
      renderTable(result, false);
      // Wheat, Rye, and classifying row
      expect(await page.getByRole("row").all()).toHaveLength(3);
    });

    it("filters classification rows to the selected label after switching modes", async () => {
      const user = userEvent.setup();
      const { rerender, getByText } = renderTable(result, true);

      // Select "Wheat" in label occurrence mode
      await user.click(getByText("Wheat"));

      // Switch to classification mode
      rerender(
        <I18nextProvider i18n={i18n}>
          <ResultsTable
            result={result}
            switchTable={false}
            onSwitchTableChange={vi.fn()}
          />
        </I18nextProvider>,
      );

      // Only Wheat and classifying row visible
      await expect.element(page.getByText("Wheat")).toBeVisible();
      expect(await page.getByText("Rye").all()).toHaveLength(0);
      // classifying row always visible
      await expect
        .element(page.getByText(enMain.resultsTable.classifying))
        .toBeVisible();
    });

    it("shows all rows after deselecting a label", async () => {
      const user = userEvent.setup();
      const { rerender, getByText } = renderTable(result, true);
      await user.click(getByText("Wheat"));
      await user.click(getByText("Wheat"));

      rerender(
        <I18nextProvider i18n={i18n}>
          <ResultsTable
            result={result}
            switchTable={false}
            onSwitchTableChange={vi.fn()}
          />
        </I18nextProvider>,
      );

      expect(await page.getByRole("row").all()).toHaveLength(3);
    });
  });

  describe("i18n", () => {
    it("shows the title in English", async () => {
      renderTable(null, false);
      await expect
        .element(page.getByText(enMain.resultsTable.title))
        .toBeVisible();
    });

    it("shows the title in French", async () => {
      await i18n.changeLanguage("fr");
      renderTable(null, false);
      await expect
        .element(page.getByText(frMain.resultsTable.title))
        .toBeVisible();
    });

    it("shows 'Classifying...' text in French", async () => {
      await i18n.changeLanguage("fr");
      const result = makeResult({
        classifications: [""],
        scores: [0],
        topN: [[]],
      });
      renderTable(result, false);
      await expect
        .element(page.getByText(frMain.resultsTable.classifying))
        .toBeVisible();
    });

    it("shows 'Top results' label in French after expanding a row", async () => {
      await i18n.changeLanguage("fr");
      const result = makeResult({
        classifications: ["Wheat"],
        scores: [0.9],
        topN: [[{ score: 0.9, label: "Wheat" }]],
      });
      const user = userEvent.setup();
      const { getAllByRole } = renderTable(result, false);
      await user.click(getAllByRole("row")[0]);
      await expect
        .element(page.getByText(frMain.resultsTable.topResults))
        .toBeVisible();
    });
  });
});
