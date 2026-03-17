import { Box, Link } from "@mui/material";
import CanadaLogo from "../assets/Canada_logo.png";
import { colours } from "../styles/colours";
import { versions } from "../_versions";
import { useTranslation } from "react-i18next";

const Footer: React.FC = () => {
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
        <Link
          href="https://github.com/ai-cfia/nachet"
          sx={{
            color: colours.CFIA_Font_Black,
            fontSize: "1rem",
            textDecoration: "none",
            cursor: "pointer",
          }}
        >
          {t("developedBy")}
        </Link>
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
