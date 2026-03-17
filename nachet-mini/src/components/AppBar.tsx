import { colours } from "../styles/colours";
import { Box, Typography, Switch, Stack } from "@mui/material";
import { useTranslation } from "react-i18next";

const AppBar: React.FC = () => {
  const { t, i18n } = useTranslation("header");

  const currentLanguage = i18n.language;
  const isFrench = currentLanguage === "fr";

  const handleLanguageChange = () => {
    const newLanguage = isFrench ? "en" : "fr";
    i18n.changeLanguage(newLanguage);
  };

  return (
    <Box
      sx={{
        backgroundColor: colours.CFIA_Background_Blue,
        color: colours.CFIA_Font_White,
        height: "3.5vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        position: "sticky",
        top: 0,
        zIndex: 3,
        boxShadow: "0 0 5px 0 rgba(0, 0, 0, 0.5)",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          zIndex: 3,
          width: "100%",
          padding: "0 1.5vw",
          height: "2.8vh",
        }}
      >
        <Typography
          variant="h2"
          sx={{
            color: colours.CFIA_Font_White,
            fontSize: "1.4vh",
            fontWeight: "bold",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            justifySelf: "flex-start",
            zIndex: 3,
          }}
        >
          {t("appBar.title")}
        </Typography>
        <Stack
          direction="row"
          spacing={1}
          alignItems="center"
          sx={{ height: "100%" }}
        >
          <Typography
            sx={{
              fontSize: "1.2vh",
              color: colours.CFIA_Font_White,
              fontWeight: isFrench ? "normal" : "bold",
            }}
          >
            {t("appBar.languageToggle.en")}
          </Typography>
          <Switch
            checked={isFrench}
            onChange={handleLanguageChange}
            size="small"
            sx={{
              "& .MuiSwitch-switchBase.Mui-checked": {
                color: colours.CFIA_Font_White,
              },
              "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                backgroundColor: colours.CFIA_Font_White,
              },
              "& .MuiSwitch-track": {
                backgroundColor: colours.CFIA_Font_White,
              },
            }}
          />
          <Typography
            sx={{
              fontSize: "1.2vh",
              color: colours.CFIA_Font_White,
              fontWeight: isFrench ? "bold" : "normal",
            }}
          >
            {t("appBar.languageToggle.fr")}
          </Typography>
        </Stack>
      </Box>
    </Box>
  );
};

export default AppBar;
