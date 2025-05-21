import {
  Popover,
  Box,
  IconButton,
  FormControl,
  Button,
  Autocomplete,
  TextField,
  createFilterOptions,
  Select,
  MenuItem,
  SelectChangeEvent,
  FilterOptionsState,
  Paper,
  TableContainer,
  Table,
  TableBody,
  TableRow,
  TableCell,
  TableHead,
  Typography,
} from "@mui/material";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import { SyntheticEvent, useEffect, useMemo, useState } from "react";
import { BoxCSS, ClassData, FeedbackDataNegative } from "../../../common/types";
import Draggable from "react-draggable";
import LoadingIndicator from "../loading_indicator";

interface SimpleFeedbackFormProps {
  anchorEl: HTMLButtonElement | null;
  onClose: () => void;
  submitPositiveFeedback: () => void;
  onNegativeFeedback: () => void;
}

export const SimpleFeedbackForm = (
  props: SimpleFeedbackFormProps,
): JSX.Element => {
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
  position: BoxCSS;
  classList: ClassData[];
  onCancel: () => void;
  onSubmit: (feedbackDataNegative: FeedbackDataNegative) => void;
  isNewAnnotation: boolean;
  classListLoading: boolean;
}

export const NegativeFeedbackForm = (
  props: NegativeFeedbackFormProps,
): JSX.Element => {
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

  const defaultClass = useMemo(() => {
    return {
      id: -1,
      classId: "",
      label: "",
    };
  }, []);

  const formWidth = "300px";

  const {
    inference,
    position,
    classList,
    onCancel,
    onSubmit,
    isNewAnnotation,
    classListLoading,
  } = props;
  const [selectedClass, setSelectedClass] = useState<ClassData>(defaultClass);
  const [comment, setComment] = useState<string>(reasons[1]);

  const filter = createFilterOptions<ClassData>();

  const filteredClassList = (
    options: ClassData[],
    params: FilterOptionsState<ClassData>,
  ): ClassData[] => {
    const { inputValue } = params;
    if (inputValue === "") {
      return options;
    }
    const filtered = filter(options, params);

    // Suggest the creation of a new value
    const isExisting = options.some((option) => inputValue === option.label);
    if (inputValue !== "" && !isExisting) {
      filtered.push({
        ...defaultClass,
        label: `"${inputValue}"`,
      });
    }

    return filtered;
  };

  const getClassLabel = (option: string | ClassData): string => {
    return typeof option === "string" ? option : option.label;
  };

  const handleClassChange = (
    event: SyntheticEvent<Element, Event>,
    newValue: string | ClassData | null,
  ) => {
    event.preventDefault();
    if (newValue == null) {
      setSelectedClass(defaultClass);
    } else if (typeof newValue === "string") {
      setSelectedClass({
        ...defaultClass,
        label: newValue,
      });
    } else {
      setSelectedClass(newValue);
    }
  };

  const handleCommentChange = (event: SelectChangeEvent<string>) => {
    setComment(event.target.value);
  };

  const handleSubmit = () => {
    onSubmit({
      ...inference,
      boxes: [
        {
          ...inference.boxes[0],
          classId: selectedClass.classId,
          label: selectedClass.label,
          comment: comment,
        },
      ],
    });
  };

  const handleCancel = () => {
    onCancel();
  };

  useEffect(() => {
    if (inference != null) {
      setSelectedClass(
        classList.find((item) => {
          return item.classId === inference.boxes[0].classId;
        }) ?? defaultClass,
      );
    }
  }, [classList, defaultClass, inference]);

  useEffect(() => {
    if (comment === "No Seed") {
      setSelectedClass({
        id: -1,
        classId: "",
        label: "",
      });
    }
  }, [comment]);

  useEffect(() => {
    if (isNewAnnotation) {
      setComment(reasons[0]);
    }
  }, [isNewAnnotation, reasons]);

  return (
    <Draggable
      defaultPosition={{
        x: position.left - parseInt(formWidth.slice(0, -2)) - 10,
        y: position.top,
      }}
      bounds="parent"
      disabled={false}
    >
      <Box
        sx={{
          id: "negative-feedback",
          position: "absolute",
          zIndex: 500,
          backgroundColor: "white",
          border: "2px solid black",
          padding: "10px",
          minWidth: formWidth,
          minHeight: "5px",
          borderRadius: "10px",
          justifyContent: "center",
        }}
      >
        <FormControl size="small" sx={{ width: "100%", alignItems: "center" }}>
          <Typography
            variant="h5"
            sx={{ textAlign: "center", marginBottom: "10px" }}
          >
            Feedback
          </Typography>

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
                      {inference.boxes[0].box.topX.toFixed(2)}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>TopY</TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {inference.boxes[0].box.topY.toFixed(2)}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>BottomX</TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {inference.boxes[0].box.bottomX.toFixed(2)}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>BottomY</TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      {inference.boxes[0].box.bottomY.toFixed(2)}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
            {classListLoading ? (
              <LoadingIndicator />
            ) : (
              <Autocomplete
                id="feedback-class"
                renderInput={(params) => (
                  <TextField {...params} label="Class" />
                )}
                options={classList}
                value={selectedClass}
                onChange={handleClassChange}
                isOptionEqualToValue={(option, value) =>
                  option.label === value.label
                }
                filterOptions={filteredClassList}
                disablePortal
                selectOnFocus
                clearOnBlur
                handleHomeEndKeys
                freeSolo={comment === "Wrong Seed not in List"}
                getOptionLabel={getClassLabel}
                sx={{
                  marginTop: "20px",
                  width: "100%",
                }}
                disabled={comment === "No Seed"}
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
    </Draggable>
  );
};
