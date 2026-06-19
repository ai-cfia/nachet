import { useEffect } from "react";
import { initializeApi } from "../common/api";
import { errorLogger } from "../logging";
import { useNachetAuth } from "./NachetAuthContext";

export function AuthApiBridge() {
  const { getAccessToken } = useNachetAuth();

  useEffect(() => {
    initializeApi(getAccessToken);
    errorLogger.setTokenProvider(async () => getAccessToken());
  }, [getAccessToken]);

  return null;
}
