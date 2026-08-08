import React, { useState } from "react";
import {
  Table,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  Box,
  CardHeader,
  CircularProgress,
  IconButton,
} from "@mui/material";
import SwitchLeftIcon from "@mui/icons-material/SwitchLeft";
import CropFreeIcon from "@mui/icons-material/CropFree";
import LabelIcon from "@mui/icons-material/Label";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import type { InferenceResult } from "@common/types";
import { useTranslation } from "react-i18next";
import SeedInspector from "@components/SeedInspector";
import { useInferenceStore } from "@stores/useInferenceStore";

interface Props {
  result: InferenceResult | null;
  switchTable: boolean;
  onSwitchTableChange: (value: boolean) => void;
  activeResultKey: string | null;
  imageSrc: string | undefined;
  imageDims: number[];
  selectedBoxId: string | null;
  onSelectedBoxIdChange: (boxId: string | null) => void;
}

const ResultsTable = ({
  result,
  switchTable,
  onSwitchTableChange,
  activeResultKey,
  imageSrc,
  imageDims,
  selectedBoxId,
  onSelectedBoxIdChange,
}: Props) => {
  const { t } = useTranslation("main");
  const [selectedLabel, setSelectedLabel] = useState<string>("all");
  const camResults = useInferenceStore((state) => state.camResults);

  const handleSelect = (key: string): void => {
    setSelectedLabel(selectedLabel === key ? "all" : key);
  };

  const labelOccurrence = result?.labelOccurrence ?? {};
  const classifications = result?.classifications ?? [];
  const topN = result?.topN ?? [];
  const scores = result?.scores ?? [];

  return (
    <Box
      sx={{
        width: "100%",
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        border: "0.01vh solid LightGrey",
        borderRadius: "0.4vh",
      }}
      boxShadow={0}
      data-testid="results-table-component"
    >
      <CardHeader
        title={t("resultsTable.title")}
        titleTypographyProps={{
          variant: "h6",
          align: "left",
          fontWeight: 600,
          fontSize: "1.3vh",
          color: "text.primary",
        }}
        sx={{ padding: "0.8vh 1vh 0.8vh 0.8vh", flexShrink: 0 }}
        action={
          <IconButton
            sx={{ padding: 0, marginTop: "0.27vh", marginRight: "0.4vh" }}
            onClick={() => {
              onSwitchTableChange(!switchTable);
            }}
            disabled
            aria-label="switch table view"
          >
            <SwitchLeftIcon
              style={{
                color: "#1565c0",
                fontSize: "2vh",
                marginTop: "0.1vh",
                marginBottom: "0.1vh",
                marginRight: "0.1vh",
              }}
            />
          </IconButton>
        }
      />

      <TableContainer
        sx={{
          overflow: "auto",
          flex: 1,
          minHeight: 0,
          border: 0,
          borderTopRightRadius: 0,
          borderTopLeftRadius: 0,
          borderTop: "0.01vh solid LightGrey",
          borderBottom: 0,
          boxShadow: "none",
        }}
      >
        <Table sx={{ borderBottom: 0 }}>
          <TableBody sx={{ borderBottom: 0 }}>
            {/* Label occurrence table */}
            {switchTable &&
              Object.keys(labelOccurrence).map((key, i) => (
                <TableRow
                  key={i}
                  aria-selected={selectedLabel === key}
                  sx={{
                    backgroundColor:
                      selectedLabel === key ? "#F5F5F5" : "#ffffff",
                    "&:hover": {
                      backgroundColor: "#F5F5F5",
                      transition: "0.1s ease-in-out all",
                    },
                  }}
                >
                  <TableCell
                    align="left"
                    sx={{
                      cursor: "pointer",
                      paddingRight: 0,
                      fontSize: "1.0vh",
                      paddingTop: "0.5vh",
                      paddingBottom: "0.5vh",
                      paddingLeft: "0.8vh",
                      color: "text.primary",
                    }}
                    onClick={() => {
                      handleSelect(key);
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <LabelIcon
                        style={{
                          color: "#1565c0",
                          fontSize: "1.8vh",
                          paddingRight: "0.3vw",
                        }}
                      />
                      <span style={{ width: "0.7vw", textAlign: "left" }}>
                        {i + 1}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell
                    align="center"
                    sx={{
                      cursor: "pointer",
                      paddingRight: 0,
                      fontSize: "1.0vh",
                      paddingLeft: 0,
                      paddingTop: "0.5vh",
                      paddingBottom: "0.5vh",
                      color: "text.primary",
                    }}
                    onClick={() => {
                      handleSelect(key);
                    }}
                  >
                    {key}
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      paddingRight: 0,
                      fontSize: "1.15vh",
                      paddingTop: "0.5vh",
                      paddingBottom: "0.5vh",
                      paddingLeft: "0.8vh",
                      color: "text.primary",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "flex-end",
                        flexWrap: "wrap",
                      }}
                    >
                      <span style={{ width: "0.7vw", textAlign: "right" }}>
                        {labelOccurrence[key]}
                      </span>
                      <CropFreeIcon
                        style={{
                          color: "#1565c0",
                          fontSize: "1.7vh",
                          paddingLeft: "0.3vw",
                        }}
                      />
                    </div>
                  </TableCell>
                </TableRow>
              ))}

            {/* Classification detail table */}
            {!switchTable &&
              classifications.map((prediction, classIdx) => {
                const box = result?.boxes[classIdx];
                if (!box) return null;
                const rowId = `box-${box.boxId}`;
                const boxTopN = topN[classIdx] ?? [];
                const hasTopResults = boxTopN.length > 0;
                const score = boxTopN[0]?.score ?? scores[classIdx] ?? 0;
                const isExpanded = selectedBoxId === box.boxId;
                const isBoxClassifying = prediction === "";
                const isExpandable =
                  !isBoxClassifying && hasTopResults && Boolean(imageSrc);
                const cam = activeResultKey
                  ? camResults.get(`${activeResultKey}:${box.boxId}`)
                  : undefined;
                const visible =
                  selectedLabel === "all" ||
                  selectedLabel === prediction ||
                  isBoxClassifying;
                const toggleInspection = () => {
                  if (isExpandable) {
                    onSelectedBoxIdChange(isExpanded ? null : box.boxId);
                  }
                };

                if (!visible) return null;

                return (
                  <React.Fragment key={rowId}>
                    <TableRow
                      aria-expanded={isExpandable ? isExpanded : undefined}
                      aria-selected={isExpanded}
                      tabIndex={isExpandable ? 0 : undefined}
                      sx={{
                        backgroundColor: isExpanded ? "action.selected" : null,
                        "&:hover": {
                          backgroundColor: "#F5F5F5",
                          transition: "0.1s ease-in-out all",
                        },
                      }}
                      onClick={toggleInspection}
                      onKeyDown={(event) => {
                        if (
                          isExpandable &&
                          (event.key === "Enter" || event.key === " ")
                        ) {
                          event.preventDefault();
                          toggleInspection();
                        }
                      }}
                    >
                      <TableCell
                        align="left"
                        sx={{
                          cursor: isExpandable ? "pointer" : "default",
                          paddingRight: 0,
                          fontSize: "1.0vh",
                          paddingTop: "0.5vh",
                          paddingBottom: "0.5vh",
                          paddingLeft: "0.8vh",
                        }}
                      >
                        <Box
                          component="span"
                          sx={{
                            whiteSpace: "nowrap",
                            color: isBoxClassifying
                              ? "text.secondary"
                              : "text.primary",
                            fontWeight: 500,
                          }}
                        >
                          {t("resultsTable.seedNumber", {
                            number: classIdx + 1,
                          })}
                        </Box>
                      </TableCell>
                      <TableCell
                        align="center"
                        sx={{
                          cursor: isExpandable ? "pointer" : "default",
                          paddingRight: 0,
                          fontSize: "1.0vh",
                          paddingLeft: 0,
                          paddingTop: "0.5vh",
                          paddingBottom: "0.5vh",
                          color: isBoxClassifying
                            ? "text.secondary"
                            : "inherit",
                        }}
                      >
                        {isBoxClassifying ? (
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              gap: 0.5,
                            }}
                          >
                            <CircularProgress
                              size={12}
                              sx={{ color: "text.secondary" }}
                            />
                            <span>{t("resultsTable.classifying")}</span>
                          </Box>
                        ) : (
                          prediction
                        )}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{
                          cursor: isExpandable ? "pointer" : "default",
                          paddingLeft: 0,
                          fontSize: "1.0vh",
                          paddingTop: "0.5vh",
                          paddingBottom: "0.5vh",
                          paddingRight: "0.8vh",
                          color: isBoxClassifying
                            ? "text.secondary"
                            : "inherit",
                        }}
                      >
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "flex-end",
                            gap: 0.25,
                          }}
                        >
                          <span>
                            {isBoxClassifying
                              ? "..."
                              : `${(score * 100).toFixed(0)}%`}
                          </span>
                          {isExpandable &&
                            (isExpanded ? (
                              <KeyboardArrowUpIcon
                                aria-hidden
                                sx={{ fontSize: "1.6vh" }}
                              />
                            ) : (
                              <KeyboardArrowDownIcon
                                aria-hidden
                                sx={{ fontSize: "1.6vh" }}
                              />
                            ))}
                        </Box>
                      </TableCell>
                    </TableRow>
                    {isExpanded && isExpandable && (
                      <TableRow>
                        <TableCell colSpan={3} sx={{ p: 1.25 }}>
                          <SeedInspector
                            imageSrc={imageSrc ?? ""}
                            imageDims={imageDims}
                            box={box}
                            taxonomy={result?.taxonomy?.[classIdx]}
                            topResults={boxTopN}
                            cam={cam}
                          />
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                );
              })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ResultsTable;
