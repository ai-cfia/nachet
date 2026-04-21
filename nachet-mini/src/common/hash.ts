/**
 * Compute the SHA-256 hash of a base64 data-URL image.
 * Uses the Web Crypto API (crypto.subtle.digest).
 */
export const computeSha256 = async (base64DataUrl: string): Promise<string> => {
  // Strip the data-URL prefix to get raw base64
  const base64 = base64DataUrl.replace(/^data:[^;]+;base64,/, "");
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const hashBuffer = await crypto.subtle.digest("SHA-256", bytes);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}
