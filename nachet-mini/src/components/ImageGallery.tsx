import {
  Table,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  IconButton,
  Box,
  CardHeader,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import ImageIcon from "@mui/icons-material/Image";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import type { Images } from "@common/types";
import { useTranslation } from "react-i18next";

interface Props {
  images: Images[];
  currentIndex: number;
  onSelect: (index: number) => void;
  onRemove: (index: number) => void;
  onClear: () => void;
  hasResult: (index: number) => boolean;
}

const ImageGallery = ({
  images,
  currentIndex,
  onSelect,
  onRemove,
  onClear,
  hasResult,
}: Props) => {
  const { t } = useTranslation("main");

  return (
    <Box
      sx={{
        width: "100%",
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        border: "0.01vh solid LightGrey",
        borderRadius: "0.4vh",
      }}
      boxShadow={0}
      data-testid="image-gallery-component"
    >
      <CardHeader
        title={t("imageGallery.title")}
        titleTypographyProps={{
          variant: "h6",
          align: "left",
          fontWeight: 600,
          fontSize: "1.3vh",
          color: "text.primary",
        }}
        sx={{ padding: "0.8vh 1vh 0.8vh 0.8vh", flexShrink: 0 }}
        action={
          <IconButton
            sx={{ padding: 0, marginTop: "0.27vh", marginRight: "0.4vh" }}
            onClick={onClear}
            aria-label="clear all images"
            disabled={images.length === 0}
          >
            <DeleteIcon
              style={{
                color: "#1565c0",
                fontSize: "2vh",
                marginTop: "0.1vh",
                marginBottom: "0.1vh",
                marginRight: "0.1vh",
              }}
            />
          </IconButton>
        }
      />

      <TableContainer
        sx={{
          overflow: "auto",
          flex: 1,
          minHeight: 0,
          border: 0,
          borderTopRightRadius: 0,
          borderTopLeftRadius: 0,
          borderTop: "0.01vh solid LightGrey",
          borderBottom: 0,
          boxShadow: "none",
        }}
      >
        <Table sx={{ borderBottom: 0 }}>
          <TableBody sx={{ borderBottom: 0 }}>
            {images.map((item) => {
              const done = hasResult(item.index);
              return (
                <TableRow
                  key={item.index}
                  sx={{
                    backgroundColor:
                      item.index === currentIndex ? "#F5F5F5" : "#ffffff",
                    "&:hover": {
                      backgroundColor: "#F5F5F5",
                      transition: "0.1s ease-in-out all",
                    },
                  }}
                >
                  <TableCell
                    sx={{
                      cursor: "pointer",
                      paddingRight: 0,
                      fontSize: "1.1vh",
                      paddingTop: "0.5vh",
                      paddingBottom: "0.5vh",
                      paddingLeft: "0.8vh",
                      maxWidth: "11vw",
                      color: "text.primary",
                    }}
                    align="left"
                    onClick={() => {
                      onSelect(item.index);
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        flexWrap: "wrap",
                        gap: "0.3vw",
                      }}
                    >
                      <ImageIcon
                        style={{ color: "#1565c0", fontSize: "1.8vh" }}
                      />
                      <span>
                        {t("imageGallery.image", { number: item.index + 1 })}
                      </span>
                      {done && (
                        <CheckCircleIcon
                          sx={{ color: "#4caf50", fontSize: "1.6vh" }}
                          titleAccess={t("imageGallery.resultsAvailable")}
                        />
                      )}
                    </div>
                  </TableCell>

                  <TableCell
                    align="right"
                    sx={{
                      paddingLeft: 0,
                      paddingTop: "0.5vh",
                      paddingBottom: "0.5vh",
                      paddingRight: "0.8vh",
                    }}
                  >
                    <IconButton
                      onClick={() => {
                        onRemove(item.index);
                      }}
                      sx={{ padding: 0 }}
                      aria-label={`remove image ${item.index + 1}`}
                    >
                      <CloseIcon
                        style={{ color: "#1565c0", fontSize: "1.8vh" }}
                      />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ImageGallery;
