import { Box, LinearProgress, Link, Typography } from "@mui/material";
import CanadaLogo from "../assets/Canada_logo.png";
import HfLogo from "../assets/hf-logo.svg";
import { colours } from "../styles/colours";
import { versions } from "../_versions";
import { useTranslation } from "react-i18next";
import GitHubIcon from "@mui/icons-material/GitHub";
import type { ModelLoadProgress } from "@stores/useInferenceStore";

interface FooterProps {
  statusText?: string;
  isError?: boolean;
  isLoading?: boolean;
  loadProgress?: ModelLoadProgress | null;
}

const Footer: React.FC<FooterProps> = ({
  statusText,
  isError,
  isLoading,
  loadProgress,
}) => {
  const { t } = useTranslation("footer");

  return (
    <Box
      component="footer"
      sx={{
        backgroundColor: colours.CFIA_Background_White,
        width: "100%",
        height: "5vh",
        flexShrink: 0,
      }}
    >
      <Box
        sx={{
          padding: "0vh 0vh 0.8vh 0vh",
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          maxWidth: "100%",
          height: "5vh",
          margin: "auto",
          position: "relative",
          zIndex: 0,
          paddingLeft: "1.5vw",
          paddingRight: "1.5vw",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Box
            component="span"
            sx={{
              color: colours.CFIA_Background_Blue,
              fontSize: "1rem",
            }}
          >
            {t("developedBy")}
          </Box>
          <Link
            href="https://huggingface.co/cfia-ai-lab"
            target="_blank"
            rel="noopener noreferrer"
            sx={{ display: "flex", alignItems: "center" }}
          >
            <Box
              component="img"
              src={HfLogo}
              alt="Hugging Face"
              sx={{ width: "1.5rem", height: "1.5rem" }}
            />
          </Link>
          <Link
            href="https://github.com/ai-cfia"
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              display: "flex",
              alignItems: "center",
              color: colours.CFIA_Font_Black,
            }}
          >
            <GitHubIcon sx={{ fontSize: "1.5rem" }} />
          </Link>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Box
            component="span"
            sx={{
              color: colours.CFIA_Font_Black,
              fontSize: "1rem",
            }}
          >
            {versions.version
              ? t("version", { version: versions.version })
              : ""}
          </Box>
          <Link
            href="https://github.com/ai-cfia/nachet/issues"
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              color: colours.CFIA_Background_Blue,
              fontSize: "1rem",
              textDecoration: "none",
              cursor: "pointer",
            }}
          >
            {t("reportIssue")}
          </Link>
        </Box>
        {statusText && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              minWidth: 0,
            }}
          >
            <Typography
              variant="body2"
              noWrap
              sx={{
                fontSize: "1rem",
                color: isError ? "error.main" : colours.CFIA_Background_Blue,
              }}
            >
              {statusText}
            </Typography>
            {isLoading && loadProgress && (
              <Box sx={{ minWidth: "8vw", maxWidth: "12vw" }}>
                <Typography
                  variant="caption"
                  sx={{ fontSize: "0.75rem", color: "text.secondary" }}
                >
                  {loadProgress.name} {Math.round(loadProgress.progress)}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={loadProgress.progress}
                  sx={{ height: "0.4rem", borderRadius: "0.2rem" }}
                />
              </Box>
            )}
          </Box>
        )}
        <Box
          component="img"
          src={CanadaLogo}
          alt={t("canadaLogoAlt")}
          sx={{
            width: "6vw",
            zIndex: 0,
            alignSelf: "center",
            height: "fit-content",
          }}
        />
      </Box>
    </Box>
  );
};

export default Footer;
