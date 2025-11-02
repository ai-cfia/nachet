import { Snackbar, Alert, Stack } from "@mui/material";
import { useNotificationStore } from "@stores/useNotificationStore";

export function ToastNotification() {
  const { toasts, removeToast } = useNotificationStore();

  return (
    <Stack
      spacing={1}
      sx={{
        position: "fixed",
        top: 20,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 9999,
      }}
    >
      {toasts.map((toast) => (
        <Snackbar
          key={toast.id}
          open={true}
          autoHideDuration={toast.duration}
          onClose={() => removeToast(toast.id)}
          anchorOrigin={{ vertical: "top", horizontal: "center" }}
        >
          <Alert
            severity={toast.type}
            onClose={() => removeToast(toast.id)}
            sx={{ minWidth: "300px" }}
          >
            {toast.message}
          </Alert>
        </Snackbar>
      ))}
    </Stack>
  );
}
