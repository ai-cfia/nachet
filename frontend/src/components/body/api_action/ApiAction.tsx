import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import ReportGmailerrorredIcon from "@mui/icons-material/ReportGmailerrorred";
import LoadingIndicator from "../loading_indicator";
import { Box, Button, Typography } from "@mui/material";

export interface ApiActionProps {
  loading: boolean;
  success: boolean;
  error: string | null;
  dismiss: () => void;
}

export const ApiAction = (props: ApiActionProps) => {
  const { loading, success, error, dismiss } = props;

  return (
    <Box
      sx={{
        position: "absolute",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100%",
        minWidth: "100%",
      }}
    >
      <Box
        sx={{
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100px",
          minWidth: "100px",
          maxHeight: "300px",
          backgroundColor: "white",
          border: "1px solid black",
          borderRadius: "5px",
          padding: "20px",
          boxShadow: "0px 0px 10px 0px rgba(0,0,0,0.75)",
        }}
      >
        {loading && <LoadingIndicator />}
        {!loading &&
          (success ? (
            <CheckCircleOutlinedIcon
              sx={{
                color: "green",
                fontSize: 100,
              }}
            />
          ) : (
            <>
              <ReportGmailerrorredIcon
                sx={{
                  color: "red",
                  fontSize: 100,
                }}
              />
              <Typography
                variant="body2"
                sx={{ color: "red", textAlign: "center", marginBottom: "10px" }}
              >
                {error}
              </Typography>{" "}
            </>
          ))}
        {!loading && (
          <Button
            sx={{
              backgroundColor: "blue",
              color: "white",
              "&:hover": {
                backgroundColor: "blue",
                opacity: 0.5,
              },
            }}
            onClick={dismiss}
          >
            Dismiss
          </Button>
        )}
      </Box>
    </Box>
  );
};
