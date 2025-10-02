/**
 * Emotion Cache Configuration with CSP Nonce Support
 *
 * This module creates an Emotion cache instance that reads the CSP nonce
 * from the meta tag injected by the backend, enabling Material-UI to work
 * with strict Content Security Policy without 'unsafe-inline'.
 */

import createCache from "@emotion/cache";

/**
 * Get CSP nonce from meta tag in the document head.
 *
 * The backend injects a meta tag with the nonce value:
 * <meta property="csp-nonce" content="{random-nonce}">
 *
 * @returns CSP nonce string or undefined if not found
 */
export function getCSPNonce(): string | undefined {
  const metaTag = document.querySelector<HTMLMetaElement>(
    'meta[property="csp-nonce"]',
  );
  return metaTag?.getAttribute("content") || undefined;
}

/**
 * Create Emotion cache with CSP nonce support.
 *
 * This cache is used by Material-UI to inject styles with the correct nonce,
 * allowing them to pass CSP validation.
 *
 * @returns Emotion cache instance configured with nonce
 */
export function createEmotionCache() {
  const nonce = getCSPNonce();

  if (nonce) {
    console.log(
      "✅ CSP nonce found, creating Emotion cache with nonce support",
    );
  } else {
    console.warn(
      "⚠️  CSP nonce not found in meta tag. Styles may be blocked by CSP.",
    );
  }

  return createCache({
    key: "mui-style",
    nonce,
    prepend: true, // Insert styles at the beginning of <head> for proper precedence
  });
}
