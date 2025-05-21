import { useMemo } from "react";

const useBackendUrl = (): string => {
  const backendURL = useMemo(() => {
    const url = process.env.VITE_BACKEND_URL ?? "";
    if (url == null || url === "") {
      console.error("VITE_BACKEND_URL environment variable is not set.");
    }
    return url;
  }, []);
  return backendURL;
};

export default useBackendUrl;
