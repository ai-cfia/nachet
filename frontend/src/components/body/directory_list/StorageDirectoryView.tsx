import React from "react";
import {
  Table,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  Box,
  CardHeader,
  IconButton,
} from "@mui/material";
import { colours } from "../../../styles/colours";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import CloseIcon from "@mui/icons-material/Close";
import FolderIcon from "@mui/icons-material/Folder";
import FilterIcon from "@mui/icons-material/Filter";
import { AzureStorageDirectoryItem } from "../../../common/types";

interface params {
  azureStorageDir: AzureStorageDirectoryItem[];
  curDir: string;
  handleSelect: (folder: string) => void;
  handleDelete: (folder: string) => void;
  handleCreateDirectory: () => void;
}

const StorageDirectoryView: React.FC<params> = (props) => {
  const {
    azureStorageDir,
    curDir,
    handleSelect,
    handleDelete,
    handleCreateDirectory,
  } = props;
  return (
    <Box
      sx={{
        width: "100%",
        height: "22.23vh",
        border: `0.01vh solid LightGrey`,
        borderRadius: "0.4vh",
      }}
      boxShadow={0}
      data-testid="storage-directory-component"
    >
      <CardHeader
        title="DIRECTORIES"
        titleTypographyProps={{
          variant: "h6",
          align: "left",
          fontWeight: 600,
          fontSize: "1.3vh",
          color: colours.CFIA_Font_Black,
        }}
        sx={{ padding: "0.8vh 1vh 0.8vh 0.8vh" }}
        action={
          <div>
            <IconButton
              sx={{
                padding: 0,
                marginTop: "0.27vh",
                marginRight: "0.4vh",
              }}
              onClick={handleCreateDirectory}
            >
              <CreateNewFolderIcon
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
          </div>
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
        id={"container_with_scrolls"}
      >
        <Table sx={{ borderBottom: 0 }}>
          <TableBody sx={{ borderBottom: 0 }}>
            {azureStorageDir.map(
              (item: AzureStorageDirectoryItem, index: number) => (
                <TableRow
                  key={index}
                  sx={{
                    backgroundColor:
                      item.pictureSetId === curDir
                        ? "#F5F5F5"
                        : colours.CFIA_Background_White,
                    "&:hover": {
                      backgroundColor: "#F5F5F5",
                      transition: "0.1s ease-in-out all",
                    },
                  }}
                >
                  <TableCell
                    align="left"
                    sx={{
                      cursor: "pointer",
                      paddingRight: 0,
                      fontSize: "1.1vh",
                      paddingTop: "0.5vh",
                      paddingBottom: "0.5vh",
                      paddingLeft: "0.8vh",
                      width: "10vw",
                      maxWidth: "10vw",
                      textOverflow: "break-word",
                      color: colours.CFIA_Font_Black,
                    }}
                    onClick={() => {
                      handleSelect(item.pictureSetId);
                    }}
                    data-testid={"folder-icon" + (index + 1)}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <FolderIcon
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
                      <span>{item.folderName ?? item.pictureSetId}</span>
                    </div>
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      cursor: "pointer",
                      fontSize: "1.15vh",
                      paddingTop: "0.5vh",
                      paddingBottom: "0.5vh",
                      paddingLeft: "0.8vh",
                      color: colours.CFIA_Font_Black,
                    }}
                    onClick={() => {
                      handleSelect(item.pictureSetId);
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        width: "100%",
                        justifyContent: "flex-end",
                        alignContent: "center",
                        marginLeft: "1vw",
                      }}
                    >
                      <span style={{ marginRight: "0.1vw" }}>
                        {item.nbPictures}
                      </span>
                      <FilterIcon
                        style={{
                          color: colours.CFIA_Background_Blue,
                          fontSize: "1.7vh",
                          marginTop: 0,
                          marginBottom: 0,
                          paddingTop: 0,
                          paddingBottom: 0,
                          paddingLeft: "0.3vw",
                        }}
                      />
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
                        handleDelete(item.pictureSetId);
                      }}
                      sx={{ padding: 0 }}
                      disabled={item.pictureSetId === "General"}
                      data-testid={"delete-icon" + (index + 1)}
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
              ),
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default StorageDirectoryView;
