import type {
  BoxTaxonomy,
  RankedPrediction,
  SpeciesTaxonomy,
} from "@common/types";
import taxonomy101 from "./taxonomy-101spp.json";

interface Taxon {
  family: string;
  genus: string;
}

export type TaxonomyMap = Readonly<Record<string, Taxon>>;

/**
 * Classifier-label taxonomy derived from Nachet's seed data. Vicia americana
 * is provisionally mapped to Vicia/Fabaceae pending confirmation by the team.
 */
export const seedTaxonomy = taxonomy101 as TaxonomyMap;

const rankTotals = (
  totals: Map<string, number>,
  limit: number,
): RankedPrediction[] =>
  [...totals.entries()]
    .map(([label, score]) => ({ label, score }))
    .sort((a, b) => b.score - a.score || a.label.localeCompare(b.label))
    .slice(0, limit);

/**
 * Add every species probability to its family and genus totals. If even one
 * model label is unknown, return no taxonomy rather than show partial totals.
 */
export const aggregateTaxonomyProbabilities = (
  probabilities: ArrayLike<number>,
  id2label: Record<string, string>,
  taxonomy: TaxonomyMap = seedTaxonomy,
  limit = 3,
  candidateLabels: readonly string[] = [],
): BoxTaxonomy | undefined => {
  if (probabilities.length === 0 || limit < 1) return undefined;

  const familyTotals = new Map<string, number>();
  const genusTotals = new Map<string, number>();

  for (let index = 0; index < probabilities.length; index++) {
    const label = id2label[index];
    const taxon = label ? taxonomy[label] : undefined;
    const score = Number(probabilities[index]);
    if (!taxon || !Number.isFinite(score)) return undefined;

    familyTotals.set(
      taxon.family,
      (familyTotals.get(taxon.family) ?? 0) + score,
    );
    genusTotals.set(taxon.genus, (genusTotals.get(taxon.genus) ?? 0) + score);
  }

  // Candidate scores use the same complete family and genus totals shown in
  // the overall ranking; only the displayed species are retained here.
  const candidates: SpeciesTaxonomy[] = [];
  for (const label of candidateLabels) {
    const taxon = taxonomy[label];
    if (!taxon) return undefined;
    candidates.push({
      label,
      family: {
        label: taxon.family,
        score: familyTotals.get(taxon.family) ?? 0,
      },
      genus: {
        label: taxon.genus,
        score: genusTotals.get(taxon.genus) ?? 0,
      },
    });
  }

  return {
    families: rankTotals(familyTotals, limit),
    genera: rankTotals(genusTotals, limit),
    candidates,
  };
};
