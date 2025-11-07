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

  // Bidirectional filter logic - Each field filters all other fields
  // When ANY field is selected, all other field options are narrowed to matching seeds
  const availableFamilies = useMemo(() => {
    if (!speciesData || speciesData.length === 0) return [];
    const filtered = speciesData.filter(
      (seed) =>
        (!genus || seed.genus === genus) &&
        (!species || seed.species === species) &&
        (!nameCode || seed.nameCode === nameCode),
    );
    return Array.from(new Set(filtered.map((seed) => seed.family))).sort();
  }, [speciesData, genus, species, nameCode]);

  const availableGenera = useMemo(() => {
    if (!speciesData || speciesData.length === 0) return [];
    const filtered = speciesData.filter(
      (seed) =>
        (!family || seed.family === family) &&
        (!species || seed.species === species) &&
        (!nameCode || seed.nameCode === nameCode),
    );
    return Array.from(new Set(filtered.map((seed) => seed.genus))).sort();
  }, [speciesData, family, species, nameCode]);

  const availableSpecies = useMemo(() => {
    if (!speciesData || speciesData.length === 0) return [];
    const filtered = speciesData.filter(
      (seed) =>
        (!family || seed.family === family) &&
        (!genus || seed.genus === genus) &&
        (!nameCode || seed.nameCode === nameCode),
    );
    return Array.from(new Set(filtered.map((seed) => seed.species))).sort();
  }, [speciesData, family, genus, nameCode]);

  const availableNameCodes = useMemo(() => {
    if (!speciesData || speciesData.length === 0) return [];
    const filtered = speciesData.filter(
      (seed) =>
        (!family || seed.family === family) &&
        (!genus || seed.genus === genus) &&
        (!species || seed.species === species),
    );
    return Array.from(new Set(filtered.map((seed) => seed.nameCode))).sort();
  }, [speciesData, family, genus, species]);

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

      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          gap: "10px",
          width: "100%",
        }}
      >
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
            width: "calc(50% - 5px)",
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
            onSpeciesChange(newValue || "");
          }}
          sx={{
            width: "calc(50% - 5px)",
          }}
          disabled={disabled}
        />
      </Box>

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
          onNameCodeChange(newValue || "");
        }}
        sx={{
          width: sx?.width || "100%",
        }}
        disabled={disabled}
      />
    </Box>
  );
};
