import { useEffect } from "react";
import { useVersionCheckStore } from "@stores/useVersionCheckStore";
import { versions } from "../_versions";

const REMOTE_VERSIONS_URL =
  "https://raw.githubusercontent.com/ai-cfia/nachet/refs/heads/main/nachet-mini/src/_versions.ts";
const CHECK_INTERVAL_MS = 60 * 60 * 1000;

const parseRemoteVersion = (text: string): string | null => {
  const match = text.match(/version:\s*["']([^"']+)["']/);
  return match ? match[1] : null;
};

const parseVersionParts = (version: string) => {
  const [withoutBuild] = version.replace(/^v/i, "").split("+", 1);
  const [core, prerelease] = withoutBuild.split("-", 2);
  const rawParts = core.split(".");
  if (rawParts.some((part) => !/^\d+$/.test(part))) return null;
  const parts = rawParts.map((part) => Number.parseInt(part, 10));

  return {
    parts,
    prerelease: prerelease?.split(".") ?? null,
  };
};

const comparePrerelease = (remote: string[], current: string[]) => {
  const length = Math.max(remote.length, current.length);
  for (let i = 0; i < length; i += 1) {
    const remotePart = remote[i];
    const currentPart = current[i];
    if (remotePart === undefined) return false;
    if (currentPart === undefined) return true;
    if (remotePart === currentPart) continue;

    const remoteNumeric = /^\d+$/.test(remotePart);
    const currentNumeric = /^\d+$/.test(currentPart);
    if (remoteNumeric && currentNumeric) {
      return Number(remotePart) > Number(currentPart);
    }
    if (remoteNumeric) return false;
    if (currentNumeric) return true;

    return remotePart > currentPart;
  }

  return false;
};

export const isRemoteVersionNewer = (remote: string, current: string) => {
  const remoteVersion = parseVersionParts(remote);
  const currentVersion = parseVersionParts(current);
  if (!remoteVersion || !currentVersion) return remote !== current;

  const length = Math.max(
    remoteVersion.parts.length,
    currentVersion.parts.length,
  );
  for (let i = 0; i < length; i += 1) {
    const remotePart = remoteVersion.parts[i] ?? 0;
    const currentPart = currentVersion.parts[i] ?? 0;
    if (remotePart > currentPart) return true;
    if (remotePart < currentPart) return false;
  }

  if (remoteVersion.prerelease === currentVersion.prerelease) return false;
  if (!remoteVersion.prerelease) return true;
  if (!currentVersion.prerelease) return false;

  return comparePrerelease(remoteVersion.prerelease, currentVersion.prerelease);
};

export const useVersionCheck = () => {
  const setRemoteVersion = useVersionCheckStore((s) => s.setRemoteVersion);
  const openDialog = useVersionCheckStore((s) => s.openDialog);

  useEffect(() => {
    const checkRemoteVersion = async () => {
      try {
        const response = await fetch(REMOTE_VERSIONS_URL, {
          cache: "no-store",
        });
        if (!response.ok) {
          console.warn(
            `Version check failed: ${response.status} ${response.statusText}`,
          );
          return;
        }
        const text = await response.text();
        const remote = parseRemoteVersion(text);
        if (!remote) {
          console.warn("Version check failed: could not parse remote version");
          return;
        }
        if (isRemoteVersionNewer(remote, versions.version)) {
          setRemoteVersion(remote);
          openDialog();
        }
      } catch (error) {
        console.warn("Version check failed:", error);
      }
    };

    void checkRemoteVersion();
    const intervalId = window.setInterval(
      () => void checkRemoteVersion(),
      CHECK_INTERVAL_MS,
    );
    const onFocus = () => void checkRemoteVersion();
    window.addEventListener("focus", onFocus);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", onFocus);
    };
  }, [setRemoteVersion, openDialog]);
};
