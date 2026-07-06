import { useEffect, useState } from "react";
import { environment } from "../../environments/environment";
import { Box, Link } from "@mui/material";
import CanadaLogo from "../../assets/Canada_logo.png";
import useBackendUrl from "@hooks/useBackendUrl";
import { pingBackend } from "@common/api";
import { colours } from "../../styles/colours";
import { useTranslation } from "react-i18next";
import { useNachetAuth } from "@auth";

const Footer: React.FC = () => {
  const { activeAccount } = useNachetAuth();
  const backendUrl = useBackendUrl();
  const { t } = useTranslation("footer");
  const [backendConnected, setBackendConnected] = useState<boolean | null>(
    null,
  );

  const isGuest = activeAccount?.isGuest ?? true;
  const userOid = activeAccount?.userId ?? "";

  // Check backend connectivity for guest users
  useEffect(() => {
    if (!isGuest || !backendUrl) {
      return;
    }

    const checkBackendConnectivity = async () => {
      try {
        const connected = await pingBackend({ backendUrl });
        setBackendConnected(connected);
      } catch (error) {
        console.error("Backend connectivity check failed:", error);
        setBackendConnected(false);
      }
    };

    // Initial check
    checkBackendConnectivity();

    // Periodic check every 30 seconds
    const interval = setInterval(checkBackendConnectivity, 30000);

    return () => clearInterval(interval);
  }, [isGuest, backendUrl]);

  return (
    <Box
      component="footer"
      sx={{
        backgroundColor: colours.CFIA_Background_White,
        width: "100%",
        height: "5vh",
      }}
    >
      <Box
        sx={{
          padding: "0vh 0vh 0.8vh 0vh",
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "space-between",
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
          href="https://github.com/ai-cfia"
          sx={{
            color: colours.CFIA_Font_Black,
            fontSize: "1rem",
            textDecoration: "none",
            cursor: "pointer",
            marginBottom: "auto",
            marginTop: "auto",
            alignSelf: "flex-start",
            zIndex: 0,
          }}
        >
          {t("developedBy")}
        </Link>
        <Box
          component="span"
          sx={{
            color: colours.CFIA_Font_Black,
            fontSize: "1rem",
            textDecoration: "none",
            cursor: "pointer",
            marginBottom: "auto",
            marginTop: "auto",
            alignSelf: "flex-start",
            zIndex: 0,
          }}
        >
          {backendConnected
            ? t("connection.connected")
            : t("connection.disconnected")}
        </Box>
        <Box
          component="span"
          sx={{
            color: colours.CFIA_Font_Black,
            fontSize: "1rem",
            textDecoration: "none",
            cursor: "pointer",
            marginBottom: "auto",
            marginTop: "auto",
            alignSelf: "flex-start",
            zIndex: 0,
          }}
        >
          {environment.version !== ""
            ? t("version", { version: environment.version })
            : ""}
        </Box>
        <Box
          component="span"
          sx={{
            color: colours.CFIA_Font_Black,
            fontSize: "1rem",
            textDecoration: "none",
            cursor: "pointer",
            marginBottom: "auto",
            marginTop: "auto",
            alignSelf: "flex-start",
            zIndex: 0,
          }}
        >
          {t("oid", { oid: userOid })}
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
