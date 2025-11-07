import {
  Popover,
  Box,
  IconButton,
  FormControl,
  Button,
  Select,
  MenuItem,
  SelectChangeEvent,
  Paper,
  TableContainer,
  Table,
  TableBody,
  TableRow,
  TableCell,
  TableHead,
  Typography,
  Modal,
} from "@mui/material";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import OpenWithOutlinedIcon from "@mui/icons-material/OpenWithOutlined";
import SaveIcon from "@mui/icons-material/Save";
import OpenInFullOutlinedIcon from "@mui/icons-material/OpenInFullOutlined";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { SpeciesData, FeedbackDataNegative } from "@common/types";
import LoadingIndicator from "../loading_indicator";
import { TaxonomicFieldsGroup } from "../taxonomic_fields_group/TaxonomicFieldsGroup";

interface SimpleFeedbackFormProps {
  anchorEl: HTMLButtonElement | null;
  onClose: () => void;
  submitPositiveFeedback: () => void;
  onNegativeFeedback: () => void;
}

export const SimpleFeedbackForm = (props: SimpleFeedbackFormProps) => {
  const { anchorEl, onClose, submitPositiveFeedback, onNegativeFeedback } =
    props;

  const open = Boolean(anchorEl);
  const id = open ? "simple-feedback" : undefined;

  const handlePositiveFeedback = () => {
    submitPositiveFeedback();
    onClose();
  };

  const handleNegativeFeedback = () => {
    onNegativeFeedback();
    onClose();
  };

  return (
    <Popover
      id={id}
      open={open}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{
        vertical: "top",
        horizontal: "center",
      }}
      transformOrigin={{
        vertical: "bottom",
        horizontal: "center",
      }}
      sx={{ backgroundColor: "transparent", boxShadow: "none", zIndex: "30" }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "center",
          alignItems: "center",
          border: `0.01vh solid LightGrey`,
          flexWrap: "wrap",
        }}
      >
        <IconButton
          sx={{ marginRight: "15px" }}
          onClick={handlePositiveFeedback}
        >
          <CheckCircleOutlinedIcon
            sx={{
              color: "green",
            }}
          />
        </IconButton>

        <IconButton size="small" onClick={handleNegativeFeedback}>
          <CancelOutlinedIcon
            sx={{
              color: "red",
            }}
          />
        </IconButton>
      </Box>
    </Popover>
  );
};

interface NegativeFeedbackFormProps {
  inference: FeedbackDataNegative;
  classList: SpeciesData[];
  onCancel: () => void;
  onSubmit: (feedbackDataNegative: FeedbackDataNegative) => void;
  isNewAnnotation: boolean;
  classListLoading: boolean;
  dragEnabled: boolean;
  onToggleDragResize: () => void;
  onSaveBox: () => void;
  boxChangesSaved: boolean;
}

export const NegativeFeedbackForm = (props: NegativeFeedbackFormProps) => {
  const { t } = useTranslation("popups");

  /* TODO: update when backend is defined Section stub convert to prop or use state when backend defined */

  const reasons = useMemo(() => {
    return [
      t("feedbackForm.negative.reasons.seedNotDetected"),
      t("feedbackForm.negative.reasons.wrongSeed"),
      t("feedbackForm.negative.reasons.noSeed"),
      t("feedbackForm.negative.reasons.multiSeed"),
      t("feedbackForm.negative.reasons.wrongSeedNotInList"),
    ];
  }, [t]);
  /* Section stub convert to prop or use state when backend defined */

  const formWidth = "300px";

  const {
    inference,
    classList,
    onCancel,
    onSubmit,
    isNewAnnotation,
    classListLoading,
    dragEnabled,
    onToggleDragResize,
    onSaveBox,
    boxChangesSaved,
  } = props;

  // Initialize taxonomic fields from inference
  const [family, setFamily] = useState<string>(
    inference?.boxes[0]?.family || "",
  );
  const [genus, setGenus] = useState<string>(inference?.boxes[0]?.genus || "");
  const [species, setSpecies] = useState<string>(
    inference?.boxes[0]?.species || "",
  );
  const [nameCode, setNameCode] = useState<string>(
    inference?.boxes[0]?.nameCode || "",
  );
  const [comment, setComment] = useState<string>(
    isNewAnnotation ? reasons[0] : reasons[1],
  );

  // Error states
  const [familyError, setFamilyError] = useState<string>("");
  const [genusError, setGenusError] = useState<string>("");
  const [speciesError, setSpeciesError] = useState<string>("");
  const [nameCodeError, setNameCodeError] = useState<string>("");

  const handleCommentChange = (event: SelectChangeEvent<string>) => {
    const newComment = event.target.value;
    setComment(newComment);

    // Clear taxonomic fields when "No Seed" is selected
    if (newComment === "No Seed") {
      setFamily("");
      setGenus("");
      setSpecies("");
      setNameCode("");
    }
  };

  const handleSubmit = () => {
    // Find the matching seedId based on taxonomic fields (family+genus+species only)
    // nameCode is not unique and should not be used for matching
    const matchingSeeds = classList.filter(
      (seed) =>
        seed.family === family &&
        seed.genus === genus &&
        seed.species === species,
    );

    if (matchingSeeds.length === 0) {
      // No matching seed found - show error
      setFamilyError("No matching seed found for selected taxonomy");
      return;
    }

    if (matchingSeeds.length > 1) {
      // Multiple seeds match - should not happen if family+genus+species is unique
      setFamilyError(
        `Multiple seeds match this taxonomy (${matchingSeeds.length} matches). Please contact support.`,
      );
      return;
    }

    const matchingSeed = matchingSeeds[0];

    onSubmit({
      ...inference,
      boxes: [
        {
          ...inference.boxes[0],
          classId: matchingSeed.seedId,
          label: matchingSeed.label || `${genus} ${species}`,
          family: family,
          genus: genus,
          species: species,
          nameCode: nameCode,
          comment: comment,
        },
      ],
    });
  };

  const handleCancel = () => {
    onCancel();
  };

  return (
    <Modal
      open={true}
      onClose={handleCancel}
      hideBackdrop={true}
      sx={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "flex-end",
        pointerEvents: "none",
      }}
    >
      <Box
        sx={{
          position: "absolute",
          top: "50%",
          right: "250px",
          transform: "translateY(-50%)",
          backgroundColor: "white",
          border: "2px solid black",
          padding: "10px",
          minWidth: formWidth,
          borderRadius: "10px",
          maxHeight: "90vh",
          overflow: "auto",
          pointerEvents: "auto",
        }}
      >
        <FormControl size="small" sx={{ width: "100%", alignItems: "center" }}>
          <Typography
            variant="h5"
            sx={{ textAlign: "center", marginBottom: "10px" }}
          >
            {t("feedbackForm.negative.title")}
          </Typography>

          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "center",
              alignItems: "center",
              marginBottom: "10px",
              border: "1px solid lightgrey",
              borderRadius: "5%",
            }}
          >
            <IconButton
              className="freeform-toolbar-button freeform-toolbar-button-blue"
              onClick={onToggleDragResize}
            >
              {dragEnabled ? (
                <OpenWithOutlinedIcon />
              ) : (
                <OpenInFullOutlinedIcon />
              )}
            </IconButton>

            <IconButton
              className={`freeform-toolbar-button ${boxChangesSaved ? "freeform-toolbar-button-green" : "freeform-toolbar-button-grey"}`}
              onClick={onSaveBox}
            >
              <SaveIcon />
            </IconButton>
          </Box>

          <>
            <TableContainer component={Paper} sx={{ maxWidth: "fit-content" }}>
              <Table
                sx={{ maxWidth: "fit-content" }}
                size="small"
                aria-label={t("feedbackForm.negative.boundingBox.heading")}
              >
                <TableHead>
                  <TableRow>
                    <TableCell>
                      {t("feedbackForm.negative.boundingBox.heading")}
                    </TableCell>
                    <TableCell>_</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell>
                      {t("feedbackForm.negative.boundingBox.topX")}
                    </TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {typeof inference.boxes[0].box.topX === "number" &&
                      isFinite(inference.boxes[0].box.topX)
                        ? inference.boxes[0].box.topX.toFixed(2)
                        : "N/A"}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>
                      {t("feedbackForm.negative.boundingBox.topY")}
                    </TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {typeof inference.boxes[0].box.topY === "number" &&
                      isFinite(inference.boxes[0].box.topY)
                        ? inference.boxes[0].box.topY.toFixed(2)
                        : "N/A"}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>
                      {t("feedbackForm.negative.boundingBox.bottomX")}
                    </TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {typeof inference.boxes[0].box.bottomX === "number" &&
                      isFinite(inference.boxes[0].box.bottomX)
                        ? inference.boxes[0].box.bottomX.toFixed(2)
                        : "N/A"}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>
                      {t("feedbackForm.negative.boundingBox.bottomY")}
                    </TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {typeof inference.boxes[0].box.bottomY === "number" &&
                      isFinite(inference.boxes[0].box.bottomY)
                        ? inference.boxes[0].box.bottomY.toFixed(2)
                        : "N/A"}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
            {classListLoading ? (
              <LoadingIndicator />
            ) : (
              <TaxonomicFieldsGroup
                speciesData={classList}
                family={family}
                genus={genus}
                species={species}
                nameCode={nameCode}
                onFamilyChange={(value) => {
                  setFamily(value);
                  if (familyError) setFamilyError("");
                }}
                onGenusChange={(value) => {
                  setGenus(value);
                  if (genusError) setGenusError("");
                }}
                onSpeciesChange={(value) => {
                  setSpecies(value);
                  if (speciesError) setSpeciesError("");
                }}
                onNameCodeChange={(value) => {
                  setNameCode(value);
                  if (nameCodeError) setNameCodeError("");
                }}
                familyError={familyError}
                genusError={genusError}
                speciesError={speciesError}
                nameCodeError={nameCodeError}
                disabled={comment === "No Seed"}
                sx={{ marginTop: "20px", width: "100%" }}
              />
            )}

            <Select
              disabled={isNewAnnotation}
              labelId="comment-select-label"
              id="feedback-comment"
              value={comment}
              label="Feedback Comment"
              onChange={handleCommentChange}
              sx={{
                marginTop: "20px",
                minWidth: "100%",
              }}
            >
              {reasons.map((reason, index) => {
                return (
                  <MenuItem key={index} value={reason}>
                    {reason}
                  </MenuItem>
                );
              })}
            </Select>
          </>

          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "space-evenly",
              alignItems: "center",
              marginTop: "20px",
              minWidth: "100%",
            }}
          >
            <Button
              sx={{
                backgroundColor: "green",
                color: "white",
                "&:hover": {
                  backgroundColor: "green",
                  opacity: 0.6,
                },
                marginRight: "10px",
              }}
              onClick={handleSubmit}
            >
              {t("feedbackForm.negative.submitButton")}
            </Button>

            <Button
              sx={{
                backgroundColor: "red",
                color: "white",
                "&:hover": {
                  backgroundColor: "red",
                  opacity: 0.5,
                },
              }}
              onClick={handleCancel}
            >
              {t("feedbackForm.negative.cancelButton")}
            </Button>
          </Box>
        </FormControl>
      </Box>
    </Modal>
  );
};
