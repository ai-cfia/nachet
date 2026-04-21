/**
 * Normalizes a filename for use as an image name.
 * - Preserves the file extension
 * - Replaces any character not in A-Za-z0-9._- with a dash
 * - Collapses consecutive dashes
 * - Trims leading/trailing dashes
 * - Truncates to 256 characters
 */
export const normalizeFileName = (fileName: string): string => {
  const extMatch = fileName.match(/\.[^.]+$/);
  const ext = extMatch ? extMatch[0].toLowerCase() : "";
  const base = fileName.replace(/\.[^.]+$/, "");
  const normalized =
    base
      .replace(/[^A-Za-zÀ-ÖØ-öø-ÿ0-9._-]/g, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 256) || "image";
  return normalized + ext;
}

/**
 * Returns null if valid, or a translation key string if invalid.
 */
export const validateImageName = (value: string): string | null => {
  if (!value) return "metadata.validation.imageNameRequired";
  if (value.length > 100) return "metadata.validation.imageNameTooLong";
  if (!/^[a-zA-Z0-9.-]+$/.test(value))
    return "metadata.validation.imageNameInvalid";
  return null;
}

export const validateDescription = (value: string): string | null => {
  if (value.length > 1000) return "metadata.validation.descriptionTooLong";
  if (value && !/^[a-zA-Z0-9 .]+$/.test(value))
    return "metadata.validation.descriptionInvalid";
  return null;
}
