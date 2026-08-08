import { describe, expect, it } from "vitest";
import { aggregateTaxonomyProbabilities, seedTaxonomy } from "../taxonomy";

const taxonomy = {
  Alpha: { family: "Family B", genus: "Genus A" },
  Beta: { family: "Family A", genus: "Genus B" },
  Gamma: { family: "Family B", genus: "Genus C" },
  Delta: { family: "Family C", genus: "Genus D" },
};

describe("aggregateTaxonomyProbabilities", () => {
  it("contains a complete mapping for the 101-species classifier", () => {
    const labels = Object.keys(seedTaxonomy);
    expect(labels).toHaveLength(101);
    expect(
      labels.every(
        (label) =>
          label.length > 0 &&
          seedTaxonomy[label].family.length > 0 &&
          seedTaxonomy[label].genus.length > 0,
      ),
    ).toBe(true);
  });

  it("sums all species probabilities into ranked family and genus totals", () => {
    const result = aggregateTaxonomyProbabilities(
      [0.35, 0.3, 0.25, 0.1],
      { 0: "Alpha", 1: "Beta", 2: "Gamma", 3: "Delta" },
      taxonomy,
    );

    expect(result).toEqual({
      families: [
        { label: "Family B", score: 0.6 },
        { label: "Family A", score: 0.3 },
        { label: "Family C", score: 0.1 },
      ],
      genera: [
        { label: "Genus A", score: 0.35 },
        { label: "Genus B", score: 0.3 },
        { label: "Genus C", score: 0.25 },
      ],
      candidates: [],
    });
  });

  it("keeps family and genus totals for the displayed species", () => {
    const result = aggregateTaxonomyProbabilities(
      [0.35, 0.3, 0.25, 0.1],
      { 0: "Alpha", 1: "Beta", 2: "Gamma", 3: "Delta" },
      taxonomy,
      3,
      ["Beta", "Alpha"],
    );

    expect(result?.candidates).toEqual([
      {
        label: "Beta",
        family: { label: "Family A", score: 0.3 },
        genus: { label: "Genus B", score: 0.3 },
      },
      {
        label: "Alpha",
        family: { label: "Family B", score: 0.6 },
        genus: { label: "Genus A", score: 0.35 },
      },
    ]);
  });

  it("orders equal totals by label", () => {
    const result = aggregateTaxonomyProbabilities(
      [0.5, 0.5],
      { 0: "Alpha", 1: "Beta" },
      taxonomy,
    );

    expect(result?.families.map(({ label }) => label)).toEqual([
      "Family A",
      "Family B",
    ]);
  });

  it("returns no taxonomy when a model label is not mapped", () => {
    expect(
      aggregateTaxonomyProbabilities(
        [0.5, 0.5],
        { 0: "Alpha", 1: "Unknown" },
        taxonomy,
      ),
    ).toBeUndefined();
  });

  it("returns no taxonomy for empty or invalid probabilities", () => {
    expect(aggregateTaxonomyProbabilities([], {}, taxonomy)).toBeUndefined();
    expect(
      aggregateTaxonomyProbabilities([Number.NaN], { 0: "Alpha" }, taxonomy),
    ).toBeUndefined();
  });
});
