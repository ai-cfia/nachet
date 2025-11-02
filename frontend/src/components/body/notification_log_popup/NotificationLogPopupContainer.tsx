import { useTranslation } from "react-i18next";
import { useNotificationStore } from "@stores/useNotificationStore";
import { useModalStore } from "@stores/useModalStore";
import NotificationLogPopupView from "./NotificationLogPopupView";

export default function NotificationLogPopupContainer() {
  const { t } = useTranslation("popups");
  const { errors, dismissError, clearAllErrors, markAllErrorsAsRead } =
    useNotificationStore();
  const { notificationLogOpen, closeNotificationLog } = useModalStore();

  // Format timestamp as actual date/time
  const formatTimestamp = (timestamp: number): string => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const handleClose = () => {
    closeNotificationLog();
  };

  const handleClearAll = () => {
    clearAllErrors();
  };

  const handleDismissError = (id: string) => {
    dismissError(id);
  };

  // Mark all errors as read when modal opens
  if (notificationLogOpen && errors.some((e) => !e.read)) {
    markAllErrorsAsRead();
  }

  const translations = {
    title: t("notifications.title"),
    emptyState: t("notifications.emptyState"),
    clearAll: t("notifications.clearAll"),
    closeButton: t("notifications.closeButton"),
  };

  return (
    <NotificationLogPopupView
      open={notificationLogOpen}
      errors={errors}
      onClose={handleClose}
      onClearAll={handleClearAll}
      onDismissError={handleDismissError}
      formatTimestamp={formatTimestamp}
      translations={translations}
    />
  );
}
