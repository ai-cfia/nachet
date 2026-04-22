/**
 * Compute the SHA-256 hash of a base64 data-URL image.
 * Uses the Web Crypto API (crypto.subtle.digest).
 */
export const computeSha256 = async (base64DataUrl: string): Promise<string> => {
  // Strip the data-URL prefix to get raw base64.
  // Data URLs start with "data:" and the base64 data begins after the first comma.
  const commaIndex = base64DataUrl.indexOf(",");
  const base64 =
    base64DataUrl.startsWith("data:") && commaIndex !== -1
      ? base64DataUrl.substring(commaIndex + 1)
      : base64DataUrl;
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const hashBuffer = await crypto.subtle.digest("SHA-256", bytes);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
};
