import { Box, Button, CircularProgress, type SxProps } from "@mui/material";
import { useTranslation } from "react-i18next";

interface PopupActionButtonsProps {
  /**
   * Handler called when save button is clicked
   */
  onSave: () => void;

  /**
   * Handler called when cancel button is clicked
   */
  onCancel: () => void;

  /**
   * Optional label for save button. If not provided, uses translation key.
   */
  saveLabel?: string;

  /**
   * Optional label for cancel button. If not provided, uses translation key.
   */
  cancelLabel?: string;

  /**
   * Disable the save button (e.g., when form is invalid)
   * @default false
   */
  disabled?: boolean;

  /**
   * Show loading spinner on save button during async operations
   * @default false
   */
  loading?: boolean;

  /**
   * Optional custom styles for the button container
   */
  sx?: SxProps;
}

/**
 * Reusable Save/Cancel button component for popups.
 * Provides centered buttons with Save on the left and Cancel on the right.
 * Supports disabled and loading states.
 */
export const PopupActionButtons: React.FC<PopupActionButtonsProps> = ({
  onSave,
  onCancel,
  saveLabel,
  cancelLabel,
  disabled = false,
  loading = false,
  sx,
}) => {
  const { t } = useTranslation("popups");

  // Use provided labels or fall back to translations
  const saveBtnLabel = saveLabel ?? t("common.save", { defaultValue: "Save" });
  const cancelBtnLabel =
    cancelLabel ?? t("common.cancel", { defaultValue: "Cancel" });

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        gap: "1vh",
        marginTop: "2vh",
        marginBottom: "1vh",
        ...sx,
      }}
    >
      {/* Save button - on the left */}
      <Button
        onClick={onSave}
        variant="contained"
        color="primary"
        disabled={disabled || loading}
        startIcon={
          loading ? <CircularProgress size={16} color="inherit" /> : undefined
        }
      >
        {saveBtnLabel}
      </Button>

      {/* Cancel button - on the right */}
      <Button onClick={onCancel} variant="outlined" color="secondary">
        {cancelBtnLabel}
      </Button>
    </Box>
  );
};
