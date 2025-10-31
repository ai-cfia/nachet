import {
  Popover,
  Box,
  IconButton,
  FormControl,
  Button,
  Autocomplete,
  TextField,
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
import { SpeciesData, FeedbackDataNegative } from "@common/types";
import LoadingIndicator from "../loading_indicator";

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
  /* TODO: update when backend is defined Section stub convert to prop or use state when backend defined */

  const reasons = useMemo(() => {
    return [
      "Seed not Detected",
      "Wrong Seed",
      "No Seed",
      "Multi Seed",
      "Wrong Seed not in List",
    ];
  }, []);
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
    inference?.boxes[0]?.name_code || "",
  );
  const [comment, setComment] = useState<string>(
    isNewAnnotation ? reasons[0] : reasons[1],
  );

  // Error states
  const [familyError, setFamilyError] = useState<string>("");
  const [genusError, setGenusError] = useState<string>("");
  const [speciesError, setSpeciesError] = useState<string>("");
  const [nameCodeError, setNameCodeError] = useState<string>("");

  // Get unique values for each taxonomic field (cascading filters)
  const availableFamilies = useMemo(() => {
    return Array.from(new Set(classList.map((seed) => seed.family))).sort();
  }, [classList]);

  const availableGenera = useMemo(() => {
    const filtered = classList.filter(
      (seed) => !family || seed.family === family,
    );
    return Array.from(new Set(filtered.map((seed) => seed.genus))).sort();
  }, [classList, family]);

  const availableSpecies = useMemo(() => {
    const filtered = classList.filter(
      (seed) =>
        (!family || seed.family === family) && (!genus || seed.genus === genus),
    );
    return Array.from(new Set(filtered.map((seed) => seed.species))).sort();
  }, [classList, family, genus]);

  const availableNameCodes = useMemo(() => {
    const filtered = classList.filter(
      (seed) =>
        (!family || seed.family === family) &&
        (!genus || seed.genus === genus) &&
        (!species || seed.species === species),
    );
    return Array.from(new Set(filtered.map((seed) => seed.name_code))).sort();
  }, [classList, family, genus, species]);

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
    // Find the matching seed_id based on taxonomic fields
    const matchingSeed = classList.find(
      (seed) =>
        seed.family === family &&
        seed.genus === genus &&
        seed.species === species &&
        seed.name_code === nameCode,
    );

    onSubmit({
      ...inference,
      boxes: [
        {
          ...inference.boxes[0],
          classId: matchingSeed?.seed_id || "",
          label: matchingSeed?.label || "",
          family: family,
          genus: genus,
          species: species,
          name_code: nameCode,
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
            Feedback
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
                aria-label="Bounding Box"
              >
                <TableHead>
                  <TableRow>
                    <TableCell>Bounding Box</TableCell>
                    <TableCell>_</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell>TopX</TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {typeof inference.boxes[0].box.topX === "number" &&
                      isFinite(inference.boxes[0].box.topX)
                        ? inference.boxes[0].box.topX.toFixed(2)
                        : "N/A"}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>TopY</TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {typeof inference.boxes[0].box.topY === "number" &&
                      isFinite(inference.boxes[0].box.topY)
                        ? inference.boxes[0].box.topY.toFixed(2)
                        : "N/A"}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>BottomX</TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {typeof inference.boxes[0].box.bottomX === "number" &&
                      isFinite(inference.boxes[0].box.bottomX)
                        ? inference.boxes[0].box.bottomX.toFixed(2)
                        : "N/A"}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>BottomY</TableCell>
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
              <>
                <Autocomplete
                  id="feedback-family"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Family"
                      error={!!familyError}
                      helperText={familyError}
                    />
                  )}
                  options={availableFamilies}
                  value={family}
                  onChange={(_event, newValue) => {
                    setFamily(newValue || "");
                    if (familyError) setFamilyError("");
                  }}
                  sx={{
                    marginTop: "20px",
                    width: "100%",
                  }}
                  disabled={comment === "No Seed"}
                />

                <Autocomplete
                  id="feedback-genus"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Genus"
                      error={!!genusError}
                      helperText={genusError}
                    />
                  )}
                  options={availableGenera}
                  value={genus}
                  onChange={(_event, newValue) => {
                    setGenus(newValue || "");
                    if (genusError) setGenusError("");
                  }}
                  sx={{
                    marginTop: "10px",
                    width: "100%",
                  }}
                  disabled={comment === "No Seed"}
                />

                <Autocomplete
                  id="feedback-species"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Species"
                      error={!!speciesError}
                      helperText={speciesError}
                    />
                  )}
                  options={availableSpecies}
                  value={species}
                  onChange={(_event, newValue) => {
                    setSpecies(newValue || "");
                    if (speciesError) setSpeciesError("");
                  }}
                  sx={{
                    marginTop: "10px",
                    width: "100%",
                  }}
                  disabled={comment === "No Seed"}
                />

                <Autocomplete
                  id="feedback-name-code"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Name Code"
                      error={!!nameCodeError}
                      helperText={nameCodeError}
                    />
                  )}
                  options={availableNameCodes}
                  value={nameCode}
                  onChange={(_event, newValue) => {
                    setNameCode(newValue || "");
                    if (nameCodeError) setNameCodeError("");
                  }}
                  sx={{
                    marginTop: "10px",
                    width: "100%",
                  }}
                  disabled={comment === "No Seed"}
                />
              </>
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
              Submit
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
              Cancel
            </Button>
          </Box>
        </FormControl>
      </Box>
    </Modal>
  );
};
