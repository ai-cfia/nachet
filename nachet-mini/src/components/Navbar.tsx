import { Box } from "@mui/material";
import CFIALogo from "../assets/CFIA_blackfont.png";
import { colours } from "../styles/colours";
import { useTranslation } from "react-i18next";

const Navbar: React.FC = () => {
  const { t } = useTranslation("header");

  return (
    <Box
      component="nav"
      sx={{
        backgroundColor: colours.CFIA_Background_White,
        color: colours.CFIA_Background_White,
        height: "4vh",
        display: "flex",
        width: "100%",
        justifyContent: "center",
        alignItems: "center",
        position: "sticky",
        top: 0,
        zIndex: 0,
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          height: "4vh",
          zIndex: 0,
          width: "100%",
          padding: "0 1.5vw",
        }}
      >
        <Box
          component="img"
          src={CFIALogo}
          alt={t("navbar.logoAlt")}
          sx={{
            width: "27vh",
            height: "fit-content",
            objectFit: "contain",
            margin: "auto",
            marginLeft: 0,
            marginRight: 0,
          }}
        />
      </Box>
    </Box>
  );
};

export default Navbar;
