import { Box } from "@mui/material";
import CircularProgress from "@mui/material/CircularProgress";

export const LoadingIndicator = (): JSX.Element => {
  return (
    <Box
      style={{
        minWidth: "100%",
        minHeight: "100%",
        display: "flex",
        justifyContent: "center",
      }}
    >
      <CircularProgress
        style={{ color: "#05486c", width: "10%", height: "10%" }}
      />
    </Box>
  );
};
