import {
  Table,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  IconButton,
  Box,
  CardHeader,
  Collapse,
  Checkbox,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import ImageIcon from "@mui/icons-material/Image";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ScienceIcon from "@mui/icons-material/Science";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import type { Images, InferenceResult } from "@common/types";
import { resultKey } from "@stores/useInferenceStore";
import { useTranslation } from "react-i18next";
import { useState } from "react";

interface Props {
  images: Images[];
  currentIndex: number;
  activeResultKey: string | null;
  onSelectImage: (index: number) => void;
  onSelectResult: (resultKey: string) => void;
  onRemoveImage: (index: number) => void;
  onRemoveResult: (resultKey: string) => void;
  onEditMetadata: (index: number) => void;
  onClear: () => void;
  getResultsForImage: (
    index: number,
  ) => Array<{ modelConfigId: string; result: InferenceResult }>;
}

const ImageGallery = ({
  images,
  currentIndex,
  activeResultKey,
  onSelectImage,
  onSelectResult,
  onRemoveImage,
  onRemoveResult,
  onEditMetadata,
  onClear,
  getResultsForImage,
}: Props) => {
  const { t } = useTranslation("main");
  const [collapsedIndices, setCollapsedIndices] = useState<Set<number>>(
    new Set(),
  );
  const [checkedImages, setCheckedImages] = useState<Set<number>>(new Set());
  const [checkedResults, setCheckedResults] = useState<Set<string>>(new Set());

  const hasChecked = checkedImages.size > 0 || checkedResults.size > 0;

  const handleImageClick = (index: number) => {
    onSelectImage(index);
    setCollapsedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

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
      data-testid="image-gallery-component"
    >
      <CardHeader
        title={t("imageGallery.title")}
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
              if (hasChecked) {
                checkedResults.forEach((key) => onRemoveResult(key));
                checkedImages.forEach((index) => onRemoveImage(index));
                setCheckedResults(new Set());
                setCheckedImages(new Set());
              } else {
                onClear();
              }
            }}
            aria-label={
              hasChecked ? t("imageGallery.removeResult") : "clear all images"
            }
            disabled={images.length === 0}
          >
            <DeleteIcon
              style={{
                color: hasChecked ? "#d32f2f" : "#1565c0",
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
            {images.map((item) => {
              const imageResults = getResultsForImage(item.index);
              const hasResults = imageResults.length > 0;
              const isExpanded = !collapsedIndices.has(item.index);

              return (
                <TableRow key={item.index} sx={{ display: "table-row" }}>
                  <TableCell colSpan={2} sx={{ padding: 0, border: 0 }}>
                    {/* Image row */}
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        backgroundColor:
                          item.index === currentIndex ? "#F5F5F5" : "#ffffff",
                        "&:hover": {
                          backgroundColor: "#F5F5F5",
                          transition: "0.1s ease-in-out all",
                        },
                        cursor: "pointer",
                        paddingTop: "0.5vh",
                        paddingBottom: "0.5vh",
                        paddingLeft: "0.8vh",
                        paddingRight: "0.8vh",
                      }}
                      onClick={() => handleImageClick(item.index)}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.3vw",
                          flex: 1,
                          fontSize: "1.3vh",
                          color: "text.primary",
                          // ...(!hasResults && { pl: "2.1vh" }),
                        }}
                      >
                        <Checkbox
                          size="small"
                          checked={checkedImages.has(item.index)}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => {
                            setCheckedImages((prev) => {
                              const next = new Set(prev);
                              if (e.target.checked) next.add(item.index);
                              else next.delete(item.index);
                              return next;
                            });
                          }}
                          sx={{
                            padding: 0,
                            "& .MuiSvgIcon-root": { fontSize: "2.4vh" },
                          }}
                        />
                        <ImageIcon
                          style={{ color: "#1565c0", fontSize: "2.4vh" }}
                        />
                        <span>
                          {item.metadata.imageName ||
                            t("imageGallery.image", {
                              number: item.index + 1,
                            })}
                        </span>
                        {hasResults && (
                          <CheckCircleIcon
                            sx={{ color: "#4caf50", fontSize: "2.4vh" }}
                            titleAccess={t("imageGallery.resultsAvailable")}
                          />
                        )}
                      </Box>

                      <IconButton
                        onClick={(e) => {
                          e.stopPropagation();
                          onEditMetadata(item.index);
                        }}
                        sx={{ padding: 0, pr: "5px", pl: "25px" }}
                        aria-label={`edit metadata image ${item.index + 1}`}
                      >
                        <EditIcon
                          style={{ color: "#1565c0", fontSize: "2.4vh" }}
                        />
                      </IconButton>
                      {/* Expand icon */}

                      <Box
                        sx={{
                          mr: "0.3vw",
                          display: "flex",
                          alignItems: "center",
                        }}
                      >
                        {isExpanded ? (
                          <ExpandLessIcon
                            sx={{ fontSize: "2.4vh", color: "#1565c0" }}
                          />
                        ) : (
                          <ExpandMoreIcon
                            sx={{ fontSize: "2.4vh", color: "#1565c0" }}
                          />
                        )}
                      </Box>
                    </Box>

                    {/* Expandable sub-entries for inference results */}
                    <Collapse in={isExpanded && hasResults}>
                      {imageResults.map(({ modelConfigId, result }) => {
                        const key = resultKey(item.index, modelConfigId);
                        const isActive = activeResultKey === key;
                        // Strip timestamp or edited suffix for display
                        const displayModelId = modelConfigId.replace(
                          /:(edited-)?\d+$/,
                          "",
                        );
                        const timeLabel = result.completedAt
                          ? (() => {
                              const d = new Date(result.completedAt);
                              const yy = String(d.getFullYear()).slice(2);
                              const mo = String(d.getMonth() + 1).padStart(
                                2,
                                "0",
                              );
                              const dd = String(d.getDate()).padStart(2, "0");
                              const hh = String(d.getHours()).padStart(2, "0");
                              const mm = String(d.getMinutes()).padStart(
                                2,
                                "0",
                              );
                              const ss = String(d.getSeconds()).padStart(
                                2,
                                "0",
                              );
                              return `${yy}${mo}${dd}${hh}${mm}${ss}`;
                            })()
                          : "";
                        return (
                          <Box
                            key={key}
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: "0.3vw",
                              pl: "3.5vh",
                              pr: "0.8vh",
                              py: "0.4vh",
                              fontSize: "1.3vh",
                              cursor: "pointer",
                              backgroundColor: isActive
                                ? "#E3F2FD"
                                : "transparent",
                              "&:hover": {
                                backgroundColor: isActive
                                  ? "#E3F2FD"
                                  : "#F5F5F5",
                              },
                              color: "text.secondary",
                              borderTop: "1px solid #f0f0f0",
                            }}
                            onClick={() => onSelectResult(key)}
                          >
                            <Checkbox
                              size="small"
                              checked={checkedResults.has(key)}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => {
                                setCheckedResults((prev) => {
                                  const next = new Set(prev);
                                  if (e.target.checked) next.add(key);
                                  else next.delete(key);
                                  return next;
                                });
                              }}
                              sx={{
                                padding: 0,
                                pl: "0px",
                                ml: "0px",
                                "& .MuiSvgIcon-root": { fontSize: "2.1vh" },
                              }}
                            />
                            <ScienceIcon
                              sx={{ fontSize: "1.8vh", color: "#7b1fa2" }}
                            />
                            <Box
                              sx={{
                                flex: 1,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {t("imageGallery.resultEntry", {
                                modelId: displayModelId,
                                time: timeLabel,
                              })}
                            </Box>
                            <Box
                              sx={{
                                fontSize: "1.35vh",
                                color: "text.disabled",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {t("imageGallery.boxes", {
                                count: result.totalBoxes,
                              })}
                            </Box>
                          </Box>
                        );
                      })}
                    </Collapse>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ImageGallery;
