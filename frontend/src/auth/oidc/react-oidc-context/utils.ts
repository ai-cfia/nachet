/*
 * Borrowed and adapted from react-oidc-context utils.ts:
 * https://github.com/authts/react-oidc-context/blob/main/src/utils.ts
 *
 * Original project is MIT licensed. See LICENSE in this directory.
 */
export function hasAuthParams(location = window.location): boolean {
  const searchParams = new URLSearchParams(location.search);
  const hashParams = new URLSearchParams(location.hash.replace(/^#/, ""));

  return (
    ((searchParams.has("code") || searchParams.has("error")) &&
      searchParams.has("state")) ||
    ((hashParams.has("code") || hashParams.has("error")) &&
      hashParams.has("state"))
  );
}

export function toError(error: unknown): Error {
  if (error instanceof Error) {
    return error;
  }

  return new Error(typeof error === "string" ? error : JSON.stringify(error));
}
