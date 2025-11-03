import { createTheme } from "@mui/material/styles";

/**
 * Custom Material-UI theme configuration
 *
 * Breakpoints are configured to match the application's design requirements:
 * - xs: 0px - Mobile devices
 * - sm: 600px - Small tablets
 * - md: 1200px - Narrow screen cutoff (tablets/small laptops)
 * - lg: 1536px - Desktop screens
 * - xl: 1920px - Large desktop screens
 */
export const theme = createTheme({
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 1200, // Custom narrow screen cutoff
      lg: 1536,
      xl: 1920,
    },
  },
});
