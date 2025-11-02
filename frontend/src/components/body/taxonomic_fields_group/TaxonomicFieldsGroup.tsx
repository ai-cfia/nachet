import { Autocomplete, TextField, Box } from "@mui/material";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { SpeciesData } from "@common/types";

interface TaxonomicFieldsGroupProps {
  speciesData: SpeciesData[];
  family: string;
  genus: string;
  species: string;
  nameCode: string;
  onFamilyChange: (family: string) => void;
  onGenusChange: (genus: string) => void;
  onSpeciesChange: (species: string) => void;
  onNameCodeChange: (nameCode: string) => void;
  familyError?: string;
  genusError?: string;
  speciesError?: string;
  nameCodeError?: string;
  disabled?: boolean;
  sx?: {
    marginTop?: string;
    width?: string;
  };
}

export const TaxonomicFieldsGroup = (props: TaxonomicFieldsGroupProps) => {
  const {
    speciesData,
    family,
    genus,
    species,
    nameCode,
    onFamilyChange,
    onGenusChange,
    onSpeciesChange,
    onNameCodeChange,
    familyError,
    genusError,
    speciesError,
    nameCodeError,
    disabled = false,
    sx,
  } = props;

  const { t } = useTranslation("popups");

  // Cascading filter logic - Get unique values for each taxonomic field
  const availableFamilies = useMemo(() => {
    if (!speciesData || speciesData.length === 0) return [];
    return Array.from(new Set(speciesData.map((seed) => seed.family))).sort();
  }, [speciesData]);

  const availableGenera = useMemo(() => {
    if (!speciesData || speciesData.length === 0) return [];
    const filtered = speciesData.filter(
      (seed) => !family || seed.family === family,
    );
    return Array.from(new Set(filtered.map((seed) => seed.genus))).sort();
  }, [speciesData, family]);

  const availableSpecies = useMemo(() => {
    if (!speciesData || speciesData.length === 0) return [];
    const filtered = speciesData.filter(
      (seed) =>
        (!family || seed.family === family) && (!genus || seed.genus === genus),
    );
    return Array.from(new Set(filtered.map((seed) => seed.species))).sort();
  }, [speciesData, family, genus]);

  const availableNameCodes = useMemo(() => {
    if (!speciesData || speciesData.length === 0) return [];
    const filtered = speciesData.filter(
      (seed) =>
        (!family || seed.family === family) &&
        (!genus || seed.genus === genus) &&
        (!species || seed.species === species),
    );
    return Array.from(new Set(filtered.map((seed) => seed.name_code))).sort();
  }, [speciesData, family, genus, species]);

  // Auto-fill logic: When name_code is selected, auto-populate all fields
  const handleNameCodeChange = (value: string) => {
    onNameCodeChange(value);

    if (value && speciesData && speciesData.length > 0) {
      const matchingSeed = speciesData.find((seed) => seed.name_code === value);
      if (matchingSeed) {
        onFamilyChange(matchingSeed.family);
        onGenusChange(matchingSeed.genus);
        onSpeciesChange(matchingSeed.species);
      }
    }
  };

  // Auto-fill logic: When species is selected, auto-populate family/genus if unique match exists
  const handleSpeciesChange = (value: string) => {
    onSpeciesChange(value);

    if (value && speciesData && speciesData.length > 0) {
      const matchingSeeds = speciesData.filter(
        (seed) => seed.species === value,
      );
      const uniqueFamilies = Array.from(
        new Set(matchingSeeds.map((s) => s.family)),
      );
      const uniqueGenera = Array.from(
        new Set(matchingSeeds.map((s) => s.genus)),
      );

      if (uniqueFamilies.length === 1) onFamilyChange(uniqueFamilies[0]);
      if (uniqueGenera.length === 1) onGenusChange(uniqueGenera[0]);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        width: "100%",
      }}
    >
      <Autocomplete
        id="taxonomic-family"
        renderInput={(params) => (
          <TextField
            {...params}
            label={t("taxonomicFields.familyLabel")}
            error={!!familyError}
            helperText={familyError}
          />
        )}
        options={availableFamilies}
        value={family}
        onChange={(_event, newValue) => {
          onFamilyChange(newValue || "");
        }}
        sx={{
          marginTop: sx?.marginTop || "0px",
          width: sx?.width || "100%",
        }}
        disabled={disabled}
      />

      <Autocomplete
        id="taxonomic-genus"
        renderInput={(params) => (
          <TextField
            {...params}
            label={t("taxonomicFields.genusLabel")}
            error={!!genusError}
            helperText={genusError}
          />
        )}
        options={availableGenera}
        value={genus}
        onChange={(_event, newValue) => {
          onGenusChange(newValue || "");
        }}
        sx={{
          width: sx?.width || "100%",
        }}
        disabled={disabled}
      />

      <Autocomplete
        id="taxonomic-species"
        renderInput={(params) => (
          <TextField
            {...params}
            label={t("taxonomicFields.speciesLabel")}
            error={!!speciesError}
            helperText={speciesError}
          />
        )}
        options={availableSpecies}
        value={species}
        onChange={(_event, newValue) => {
          handleSpeciesChange(newValue || "");
        }}
        sx={{
          width: sx?.width || "100%",
        }}
        disabled={disabled}
      />

      <Autocomplete
        id="taxonomic-name-code"
        renderInput={(params) => (
          <TextField
            {...params}
            label={t("taxonomicFields.nameCodeLabel")}
            error={!!nameCodeError}
            helperText={nameCodeError}
          />
        )}
        options={availableNameCodes}
        value={nameCode}
        onChange={(_event, newValue) => {
          handleNameCodeChange(newValue || "");
        }}
        sx={{
          width: sx?.width || "100%",
        }}
        disabled={disabled}
      />
    </Box>
  );
};
