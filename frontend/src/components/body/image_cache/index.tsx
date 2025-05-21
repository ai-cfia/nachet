import React from "react";
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
import { colours } from "../../../styles/colours";

interface params {
  savedImages: any[];
  setImageIndex: React.Dispatch<React.SetStateAction<number>>;
  removeImage: (src: string) => void;
  clearImageCache: () => void;
  imageIndex: number;
  windowSize: {
    width: number;
    height: number;
  };
}

const ImageCache: React.FC<params> = (props) => {
  return (
    <Box
      sx={{
        width: "100%",
        height: "22.23vh",
        border: `0.01vh solid LightGrey`,
        borderRadius: "0.4vh",
        marginTop: "0.95vh",
        marginBottom: "0.95vh",
      }}
      boxShadow={0}
      data-testid="image-cache-component"
    >
      <CardHeader
        title="CAPTURES"
        titleTypographyProps={{
          variant: "h6",
          align: "left",
          fontWeight: 600,
          fontSize: "1.3vh",
          color: colours.CFIA_Font_Black,
        }}
        sx={{ padding: "0.8vh 1vh 0.8vh 0.8vh" }}
        action={
          <IconButton
            sx={{ padding: 0, marginTop: "0.27vh", marginRight: "0.4vh" }}
            onClick={() => {
              props.clearImageCache();
            }}
          >
            <DeleteIcon
              style={{
                color: colours.CFIA_Background_Blue,
                fontSize: "2vh",
                marginTop: "0.1vh",
                marginBottom: "0.1vh",
                marginRight: "0.1vh",
                paddingTop: 0,
                paddingBottom: 0,
              }}
            />
          </IconButton>
        }
      />
      <TableContainer
        sx={{
          overflow: "auto",
          height: "18.465vh", // 18.75
          maxHeight: "18.465vh",
          border: 0,
          borderTopRightRadius: 0,
          borderTopLeftRadius: 0,
          borderTop: `0.01vh solid LightGrey`,
          borderBottom: 0,
          boxShadow: "none",
        }}
        id={"container_with_scrolls_"}
      >
        <Table sx={{ borderBottom: 0 }}>
          <TableBody sx={{ borderBottom: 0 }}>
            {props.savedImages.map((item: any, i) => (
              <TableRow
                key={i}
                sx={{
                  backgroundColor:
                    item.index === props.imageIndex
                      ? "#F5F5F5"
                      : colours.CFIA_Background_White,
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
                    width: "11vw",
                    maxWidth: "11vw",
                    textOverflow: "break-word",
                    color: colours.CFIA_Font_Black,
                  }}
                  align="left"
                  onClick={() => {
                    props.setImageIndex(item.index);
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      flexWrap: "wrap",
                    }}
                  >
                    <ImageIcon
                      style={{
                        color: colours.CFIA_Background_Blue,
                        fontSize: "1.8vh",
                        marginTop: 0,
                        marginBottom: 0,
                        paddingTop: 0,
                        paddingBottom: 0,
                        paddingRight: "0.3vw",
                      }}
                    />
                    <span style={{ textAlign: "right" }}>
                      Capture {item.index}
                    </span>
                  </div>
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    cursor: "pointer",
                    paddingLeft: 0,
                    fontSize: "1.0vh",
                    paddingTop: "0.5vh",
                    paddingBottom: "0.5vh",
                    paddingRight: "0.8vh",
                  }}
                >
                  <IconButton
                    onClick={() => {
                      props.removeImage(item.index);
                    }}
                    sx={{ padding: 0 }}
                  >
                    <CloseIcon
                      style={{
                        color: colours.CFIA_Background_Blue,
                        fontSize: "1.8vh",
                        marginTop: 0,
                        marginBottom: 0,
                        paddingTop: 0,
                        paddingBottom: 0,
                      }}
                    />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ImageCache;
