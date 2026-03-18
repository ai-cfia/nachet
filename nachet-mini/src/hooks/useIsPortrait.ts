import { useEffect, useState } from "react";

export const useIsPortrait = () => {
  const [isPortrait, setIsPortrait] = useState(
    () => window.matchMedia("(orientation: portrait)").matches,
  );

  useEffect(() => {
    const mql = window.matchMedia("(orientation: portrait)");
    const handler = (e: MediaQueryListEvent) => setIsPortrait(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isPortrait;
};
