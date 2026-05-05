import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { NachetMini } from "@components/NachetMiniContainer";

const theme = createTheme({
  components: {
    MuiButton: {
      styleOverrides: {
        outlined: {
          borderColor: "#1565c0",
          "&:hover": { borderColor: "#1565c0" },
          "&.Mui-disabled": { borderColor: "LightGrey" },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        notchedOutline: {
          borderColor: "#1565c0",
        },
        root: {
          "&:hover .MuiOutlinedInput-notchedOutline": {
            borderColor: "#1565c0",
          },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
            borderColor: "#1565c0",
          },
          "&.Mui-disabled .MuiOutlinedInput-notchedOutline": {
            borderColor: "LightGrey",
          },
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <NachetMini />
    </ThemeProvider>
  );
}

export default App;
