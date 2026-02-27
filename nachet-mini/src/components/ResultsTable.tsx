import React, { useState } from "react";
import {
  Table,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  Box,
  CardHeader,
  IconButton,
  Typography,
} from "@mui/material";
import SwitchLeftIcon from "@mui/icons-material/SwitchLeft";
import CropFreeIcon from "@mui/icons-material/CropFree";
import LabelIcon from "@mui/icons-material/Label";
import type { InferenceResult } from "@common/types";

interface Props {
  result: InferenceResult | null;
  switchTable: boolean;
  onSwitchTableChange: (value: boolean) => void;
}

const ResultsTable = ({ result, switchTable, onSwitchTableChange }: Props) => {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<string>("all");

  const handleSelect = (key: string): void => {
    setSelectedLabel(selectedLabel === key ? "all" : key);
  };

  const handleRowClick = (rowId: string): void => {
    setExpandedRow(expandedRow === rowId ? null : rowId);
  };

  const renderTopResults = (topN: Array<{ score: number; label: string }>) => (
    <>
      <Typography
        variant="subtitle2"
        style={{
          fontWeight: "bold",
          marginTop: "-15px",
          paddingTop: "0px",
          paddingBottom: "4px",
          fontSize: "0.75em",
        }}
      >
        Top results
      </Typography>
      {topN.map((item, i) => {
        const pct =
          item.score > 0 && item.score < 0.0001
            ? "< 0.01%"
            : `${(item.score * 100).toFixed(2)}%`;
        return (
          <Typography
            key={i}
            variant="body2"
            style={{
              fontSize: "0.75em",
              paddingTop: "1px",
              paddingBottom: "1px",
            }}
          >
            {`${i + 1}. ${item.label}: ${pct}`}
          </Typography>
        );
      })}
    </>
  );

  const labelOccurrence = result?.labelOccurrence ?? {};
  const classifications = result?.classifications ?? [];
  const topN = result?.topN ?? [];
  const scores = result?.scores ?? [];

  return (
    <Box
      sx={{
        width: "100%",
        height: "22.23vh",
        border: "0.01vh solid LightGrey",
        borderRadius: "0.4vh",
      }}
      boxShadow={0}
      data-testid="results-table-component"
    >
      <CardHeader
        title="Classification Results"
        titleTypographyProps={{
          variant: "h6",
          align: "left",
          fontWeight: 600,
          fontSize: "1.3vh",
          color: "text.primary",
        }}
        sx={{ padding: "0.8vh 1vh 0.8vh 0.8vh" }}
        action={
          <IconButton
            sx={{ padding: 0, marginTop: "0.27vh", marginRight: "0.4vh" }}
            onClick={() => {
              onSwitchTableChange(!switchTable);
            }}
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
          height: "18.465vh",
          maxHeight: "18.465vh",
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
                const rowId = `box-${classIdx}`;
                const boxTopN = topN[classIdx] ?? [];
                const score = scores[classIdx] ?? 0;
                const isExpanded = expandedRow === rowId;
                const visible =
                  selectedLabel === "all" || selectedLabel === prediction;

                if (!visible) return null;

                return (
                  <React.Fragment key={rowId}>
                    <TableRow
                      sx={{
                        "&:hover": {
                          backgroundColor: "#F5F5F5",
                          transition: "0.1s ease-in-out all",
                        },
                      }}
                      onClick={() => {
                        handleRowClick(rowId);
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
                            {classIdx + 1}
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
                        }}
                      >
                        {prediction}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{
                          cursor: "pointer",
                          paddingLeft: 0,
                          fontSize: "1.0vh",
                          paddingTop: "0.5vh",
                          paddingBottom: "0.5vh",
                          paddingRight: "0.8vh",
                        }}
                      >
                        {(score * 100).toFixed(0)}%
                      </TableCell>
                    </TableRow>
                    {isExpanded && (
                      <TableRow>
                        <TableCell colSpan={3}>
                          <Box p={2}>
                            {boxTopN.length > 0 && renderTopResults(boxTopN)}
                          </Box>
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
