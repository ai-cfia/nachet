// Classification Results
// \src\components\body\classification_results\index.tsx
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
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { colours } from "../../../styles/colours";
import SwitchLeftIcon from "@mui/icons-material/SwitchLeft";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import CropFreeIcon from "@mui/icons-material/CropFree";
import LabelIcon from "@mui/icons-material/Label";
import Typography from "@mui/material/Typography";
import { useImageStore } from "@stores/useImageStore";
import { useInferenceResultsStore } from "@stores/useInferenceResultsStore";

interface params {
  labelOccurrences: any;
}

const ClassificationResults: React.FC<params> = (props) => {
  const { t } = useTranslation("main");

  const { images: savedImages, currentIndex: imageIndex } = useImageStore();
  const getResult = useInferenceResultsStore((state) => state.getResult);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<string>("all");
  const [switchTable, setSwitchTable] = useState<boolean>(true);

  // Get current image and its active inference result
  const currentImage = savedImages.find((img) => img.index === imageIndex);
  const activeWorkflowId = currentImage?.activeWorkflowId;
  const activeResult = activeWorkflowId ? getResult(activeWorkflowId) : null;
  const modelDisplayName = activeResult?.pipeline_name || "";

  const handleSelect = (key: string): void => {
    if (key === selectedLabel) {
      setSelectedLabel("all");
    } else {
      setSelectedLabel(key);
    }
  };

  const handleRowClick = (rowId: string): void => {
    // Toggle expanded row. Collapse if the same row is clicked again.
    if (expandedRow === rowId) {
      setExpandedRow(null);
    } else {
      setExpandedRow(rowId);
    }
  };

  const renderTopResults = (
    topN: Array<{ score: number | string; label: string }>,
  ) => {
    return (
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
          {t("classificationResults.topResults")}
        </Typography>
        {topN.map((result, index) => {
          // Parse the score to a float if it's a string, then immediately declare it as a const.
          const score =
            typeof result.score === "number"
              ? result.score
              : parseFloat(result.score);

          // Convert the score to a percentage string, handling very small numbers.
          const percentageString =
            score > 0 && score < 0.0001
              ? "< 0.01%" // If the score is greater than 0 but less than 0.01%, show '< 0.01%'
              : `${(score * 100).toFixed(2)}%`; // Otherwise, convert to percentage and format

          return (
            <Typography
              key={index}
              variant="body2"
              style={{
                fontSize: "0.75em",
                paddingTop: "1px",
                paddingBottom: "1px",
              }}
            >
              {`${index + 1}. ${result.label}: ${percentageString}`}
            </Typography>
          );
        })}
      </>
    );
  };

  return (
    <Box
      sx={{
        width: "100%",
        height: "22.23vh", // "22.425vh"
        border: `0.01vh solid LightGrey`,
        borderRadius: "0.4vh",
      }}
      boxShadow={0}
      data-testid="classification-results-component"
    >
      <CardHeader
        title={
          <span>
            {t("classificationResults.title")}
            {" | "}
            <strong>{modelDisplayName}</strong>
          </span>
        }
        titleTypographyProps={{
          variant: "h6",
          align: "left",
          fontWeight: 600,
          fontSize: "1.3vh",
          color: colours.CFIA_Font_Black,
        }}
        sx={{ padding: "0.8vh 1vh 0.8vh 0.8vh" }}
        action={
          <>
            <IconButton
              sx={{ padding: 0, marginTop: "0.27vh", marginRight: "0.4vh" }}
              onClick={() => {
                setSwitchTable(!switchTable);
              }}
            >
              <SwitchLeftIcon
                style={{
                  color: colours.CFIA_Background_Blue,
                  fontSize: "2vh",
                  marginTop: "0.1vh",
                  marginBottom: "0.1vh",
                  marginRight: "0.1vh",
                  paddingTop: 0,
                  paddingBottom: 0,
                }}
              />
            </IconButton>
          </>
        }
      />
      <TableContainer
        sx={{
          overflow: "auto",
          height: "18.465vh", // 18.75
          maxHeight: "18.465vh",
          border: 0,
          borderTopRightRadius: 0,
          borderTopLeftRadius: 0,
          borderTop: `0.01vh solid LightGrey`,
          borderBottom: 0,
          boxShadow: "none",
        }}
        id={"container_with_scrolls"}
      >
        <Table sx={{ borderBottom: 0 }}>
          <TableBody sx={{ borderBottom: 0 }}>
            {switchTable &&
              Object.keys(props.labelOccurrences).map((key, index) => (
                <TableRow
                  key={index}
                  sx={{
                    backgroundColor:
                      selectedLabel === key
                        ? "#F5F5F5"
                        : colours.CFIA_Background_White,
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
                      color: colours.CFIA_Font_Black,
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
                          color: colours.CFIA_Background_Blue,
                          fontSize: "1.8vh",
                          marginTop: 0,
                          marginBottom: 0,
                          paddingTop: 0,
                          paddingBottom: 0,
                          paddingRight: "0.3vw",
                        }}
                      />
                      <span style={{ width: "0.7vw", textAlign: "left" }}>
                        {index + 1}
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
                      color: colours.CFIA_Font_Black,
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
                      cursor: "pointer",
                      paddingRight: 0,
                      fontSize: "1.15vh",
                      paddingTop: "0.5vh",
                      paddingBottom: "0.5vh",
                      paddingLeft: "0.8vh",
                      color: colours.CFIA_Font_Black,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "right",
                        flexWrap: "wrap",
                      }}
                    >
                      <span style={{ width: "0.7vw", textAlign: "right" }}>
                        {props.labelOccurrences[key]}
                      </span>
                      <CropFreeIcon
                        style={{
                          color: colours.CFIA_Background_Blue,
                          fontSize: "1.7vh",
                          marginTop: 0,
                          marginBottom: 0,
                          paddingTop: 0,
                          paddingBottom: 0,
                          paddingLeft: "0.3vw",
                        }}
                      />
                    </div>
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
                    <IconButton
                      onClick={() => {
                        console.log("more options");
                      }}
                      sx={{ padding: 0 }}
                    >
                      <MoreVertIcon
                        style={{
                          color: colours.CFIA_Background_Blue,
                          fontSize: "1.8vh",
                          marginTop: 0,
                          marginBottom: 0,
                          paddingTop: 0,
                          paddingBottom: 0,
                        }}
                      />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}

            {!switchTable &&
              savedImages.map((object: any, objectIndex: number) => {
                if (object.index === imageIndex && object.annotated === true) {
                  return object.classifications.map(
                    (prediction: any, classificationIndex: number) => {
                      const rowId = `${objectIndex}-${classificationIndex}`;
                      const topN = object.topN[classificationIndex];
                      const isExpanded = expandedRow === rowId;
                      const labelMatchesSelection =
                        selectedLabel === "all" || selectedLabel === prediction;

                      if (labelMatchesSelection) {
                        return (
                          <React.Fragment key={rowId}>
                            <TableRow
                              key={rowId}
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
                                      color: colours.CFIA_Background_Blue,
                                      fontSize: "1.8vh",
                                      marginTop: 0,
                                      marginBottom: 0,
                                      paddingTop: 0,
                                      paddingBottom: 0,
                                      paddingRight: "0.3vw",
                                    }}
                                  />
                                  <span
                                    style={{
                                      width: "0.7vw",
                                      textAlign: "left",
                                    }}
                                  >
                                    {classificationIndex + 1}
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
                                {(
                                  object.scores[classificationIndex] * 100
                                ).toFixed(0)}
                                %
                              </TableCell>
                              <TableCell
                                align="left"
                                sx={{
                                  fontSize: "1.0vh",
                                  paddingTop: "0.5vh",
                                  paddingBottom: "0.5vh",
                                  paddingRight: "0.8vh",
                                }}
                              >
                                {/* Content or modifications for this cell */}
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
                                <IconButton
                                  onClick={() => {
                                    // logic to handle more options
                                  }}
                                  sx={{ padding: 0 }}
                                >
                                  <MoreVertIcon
                                    style={{
                                      color: colours.CFIA_Background_Blue,
                                      fontSize: "1.8vh",
                                      marginTop: 0,
                                      marginBottom: 0,
                                      paddingTop: 0,
                                      paddingBottom: 0,
                                    }}
                                  />
                                </IconButton>
                              </TableCell>
                            </TableRow>
                            {isExpanded && (
                              <TableRow>
                                <TableCell colSpan={6}>
                                  <Box p={2}>
                                    {topN?.length > 0 && renderTopResults(topN)}
                                  </Box>
                                </TableCell>
                              </TableRow>
                            )}
                          </React.Fragment>
                        );
                      }
                      return null;
                    },
                  );
                } else {
                  return null;
                }
              })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ClassificationResults;
