import { Component, ErrorInfo, ReactNode } from "react";
import { Box, Typography, Button, Paper } from "@mui/material";
import { withTranslation, WithTranslation } from "react-i18next";
import { errorLogger } from "../../../logging";

interface Props extends WithTranslation {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log the error to our centralized logging service
    errorLogger.logError("React Error Boundary caught an error", error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
      correlationId: errorLogger.getCorrelationId(),
    });

    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    // Optionally reload the page
    // window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { t } = this.props;

      return (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="400px"
          p={3}
        >
          <Paper elevation={3} sx={{ p: 4, maxWidth: 600 }}>
            <Typography variant="h4" color="error" gutterBottom>
              {t("errors:boundary.title")}
            </Typography>
            <Typography variant="body1" paragraph>
              {t("errors:boundary.message")}
            </Typography>
            {process.env.NODE_ENV === "development" && this.state.error && (
              <Box mt={2}>
                <Typography variant="subtitle2" color="textSecondary">
                  {t("errors:boundary.devDetails")}
                </Typography>
                <Paper
                  variant="outlined"
                  sx={{ p: 2, mt: 1, bgcolor: "grey.50" }}
                >
                  <Typography
                    variant="body2"
                    component="pre"
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.875rem",
                      overflow: "auto",
                    }}
                  >
                    {this.state.error.toString()}
                    {this.state.errorInfo &&
                      this.state.errorInfo.componentStack}
                  </Typography>
                </Paper>
              </Box>
            )}
            <Box mt={3} display="flex" gap={2}>
              <Button
                variant="contained"
                color="primary"
                onClick={this.handleReset}
              >
                {t("errors:boundary.tryAgain")}
              </Button>
              <Button
                variant="outlined"
                onClick={() => (window.location.href = "/")}
              >
                {t("errors:boundary.goHome")}
              </Button>
            </Box>
            <Typography
              variant="caption"
              color="textSecondary"
              mt={2}
              display="block"
            >
              {t("errors:boundary.errorId", {
                errorId: errorLogger.getCorrelationId(),
              })}
            </Typography>
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}

const ErrorBoundaryWithTranslation = withTranslation()(ErrorBoundary);
ErrorBoundaryWithTranslation.displayName = "ErrorBoundary";

export default ErrorBoundaryWithTranslation;
