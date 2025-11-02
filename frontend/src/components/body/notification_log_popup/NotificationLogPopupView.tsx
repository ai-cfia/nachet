import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ErrorIcon from "@mui/icons-material/Error";
import WarningIcon from "@mui/icons-material/Warning";
import InfoIcon from "@mui/icons-material/Info";
import NotificationsNoneIcon from "@mui/icons-material/NotificationsNone";
import DeleteIcon from "@mui/icons-material/Delete";

interface Notification {
  id: string;
  type: "error" | "warning" | "info";
  message: string;
  timestamp: number;
  read: boolean;
  source?: string;
}

interface NotificationLogPopupViewProps {
  open: boolean;
  errors: Notification[];
  onClose: () => void;
  onClearAll: () => void;
  onDismissError: (id: string) => void;
  formatTimestamp: (timestamp: number) => string;
  translations: {
    title: string;
    emptyState: string;
    clearAll: string;
    closeButton: string;
  };
}

export default function NotificationLogPopupView({
  open,
  errors,
  onClose,
  onClearAll,
  onDismissError,
  formatTimestamp,
  translations,
}: NotificationLogPopupViewProps) {
  const getIcon = (type: "error" | "warning" | "info") => {
    switch (type) {
      case "error":
        return <ErrorIcon color="error" />;
      case "warning":
        return <WarningIcon color="warning" />;
      case "info":
        return <InfoIcon color="info" />;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">{translations.title}</Typography>
          <Box>
            {errors.length > 0 && (
              <Button
                onClick={onClearAll}
                color="primary"
                size="small"
                sx={{ mr: 1 }}
              >
                {translations.clearAll}
              </Button>
            )}
            <IconButton
              edge="end"
              color="inherit"
              onClick={onClose}
              aria-label="close"
              size="small"
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ maxHeight: "60vh", minHeight: "300px" }}>
        {errors.length === 0 ? (
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            sx={{ py: 6 }}
          >
            <NotificationsNoneIcon
              sx={{ fontSize: 64, color: "text.secondary", mb: 2 }}
            />
            <Typography color="text.secondary">
              {translations.emptyState}
            </Typography>
          </Box>
        ) : (
          <List>
            {errors.map((error, index) => (
              <ListItem
                key={error.id}
                divider={index < errors.length - 1}
                sx={{
                  alignItems: "flex-start",
                  "&:hover": {
                    backgroundColor: "action.hover",
                  },
                }}
              >
                <ListItemIcon sx={{ mt: 1 }}>
                  {getIcon(error.type)}
                </ListItemIcon>
                <ListItemText
                  primary={error.message}
                  secondary={formatTimestamp(error.timestamp)}
                  primaryTypographyProps={{
                    sx: { wordBreak: "break-word" },
                  }}
                />
                <IconButton
                  edge="end"
                  aria-label="dismiss"
                  onClick={() => onDismissError(error.id)}
                  size="small"
                  sx={{ mt: 1 }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} color="primary">
          {translations.closeButton}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
