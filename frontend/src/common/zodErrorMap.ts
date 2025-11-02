import { z, ZodIssueCode } from "zod";

/**
 * Simple helper to translate Zod validation errors to i18n keys.
 * Use this in components when displaying Zod validation errors.
 *
 * @param error - ZodError from schema.safeParse()
 * @returns Translation key for the error message
 *
 * @example
 * ```typescript
 * const validation = schema.safeParse(value);
 * if (!validation.success) {
 *   const errorKey = getZodErrorKey(validation.error);
 *   setError(t(errorKey));
 * }
 * ```
 */
export function getZodErrorKey(error: z.ZodError): string {
  // Get the first issue (most components only show the first error)
  const issue = error.issues[0];

  if (!issue) {
    return "validation.generic.invalid";
  }

  switch (issue.code) {
    case ZodIssueCode.invalid_type:
      if (
        "received" in issue &&
        (issue.received === "undefined" || issue.received === "null")
      ) {
        return "validation.generic.required";
      }
      return "validation.generic.invalidType";

    case ZodIssueCode.invalid_format:
      return "validation.generic.invalidString";

    case ZodIssueCode.invalid_value:
      return "validation.generic.invalidEnum";

    case ZodIssueCode.too_small:
      if ("type" in issue && issue.type === "string") {
        if ("minimum" in issue && issue.minimum === 1) {
          return "validation.generic.required";
        }
        return "validation.generic.tooSmallString";
      }
      return "validation.generic.tooSmall";

    case ZodIssueCode.too_big:
      if ("type" in issue && issue.type === "string") {
        return "validation.generic.tooLargeString";
      }
      return "validation.generic.tooLarge";

    case ZodIssueCode.custom:
      // For custom errors, return the custom message if available
      // Otherwise fall back to generic
      if ("message" in issue && issue.message) {
        // Check if message matches known patterns and return appropriate key
        // Otherwise return the message as-is (it's already a string)
        return issue.message;
      }
      return "validation.generic.custom";

    case ZodIssueCode.invalid_union:
    case ZodIssueCode.unrecognized_keys:
    case ZodIssueCode.invalid_key:
    case ZodIssueCode.invalid_element:
    case ZodIssueCode.not_multiple_of:
    default:
      return "validation.generic.invalid";
  }
}

/**
 * Gets interpolation values from a Zod error for translation.
 * Use this with getZodErrorKey() when the error message needs dynamic values.
 *
 * @param error - ZodError from schema.safeParse()
 * @returns Object with interpolation values
 *
 * @example
 * ```typescript
 * const validation = schema.safeParse(value);
 * if (!validation.success) {
 *   const errorKey = getZodErrorKey(validation.error);
 *   const values = getZodErrorValues(validation.error);
 *   setError(t(errorKey, values));
 * }
 * ```
 */
export function getZodErrorValues(error: z.ZodError): Record<string, unknown> {
  const issue = error.issues[0];

  if (!issue) {
    return {};
  }

  const values: Record<string, unknown> = {};

  switch (issue.code) {
    case ZodIssueCode.invalid_type:
      if ("expected" in issue && "received" in issue) {
        values.expected = String(issue.expected);
        values.received = String(issue.received);
      }
      break;

    case ZodIssueCode.too_small:
      if ("minimum" in issue) {
        values.minimum = issue.minimum;
      }
      break;

    case ZodIssueCode.too_big:
      if ("maximum" in issue) {
        values.maximum = issue.maximum;
      }
      break;
  }

  return values;
}
