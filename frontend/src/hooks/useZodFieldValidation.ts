import { useCallback } from "react";
import { ZodSchema } from "zod";
import { useTranslation } from "react-i18next";
import { getZodErrorKey } from "@common/zodErrorMap";

/**
 * Error key mapping for different Zod error codes
 * Maps to translation keys in locales/{en,fr}/validation.ts
 */
interface ErrorKeyMapping {
  too_small?: string; // e.g. "validation.imageName.empty"
  too_big?: string; // e.g. "validation.imageName.tooLong"
}

/**
 * Custom hook for Zod field validation with auto-normalization on blur
 *
 * @param schema - Zod schema to validate against
 * @param value - Current field value
 * @param setValue - Setter for field value
 * @param setError - Setter for error message
 * @param errorKeys - Mapping of Zod error codes to translation keys
 * @param namespace - i18n namespace (default: "popups")
 *
 * @returns Object with onChange and onBlur handlers
 *
 * @example
 * const { onChange, onBlur } = useZodFieldValidation(
 *   imageNameSchema,
 *   imageName,
 *   setImageName,
 *   setImageNameError,
 *   {
 *     too_small: "validation.imageName.empty",
 *     too_big: "validation.imageName.tooLong"
 *   }
 * );
 *
 * <TextField value={imageName} onChange={onChange} onBlur={onBlur} />
 */
export const useZodFieldValidation = <T>(
  schema: ZodSchema<T>,
  value: T,
  setValue: (value: T) => void,
  setError: (error: string) => void,
  errorKeys: ErrorKeyMapping,
  namespace: string = "popups",
) => {
  const { t } = useTranslation(namespace);

  const handleBlur = useCallback(() => {
    const result = schema.safeParse(value);
    if (result.success) {
      // Update with normalized value and clear error
      setValue(result.data);
      setError("");
    } else {
      // Map Zod error to translated message
      const issue = result.error.issues[0];
      const errorCode = issue.code as keyof ErrorKeyMapping;

      if (errorCode in errorKeys && errorKeys[errorCode]) {
        setError(t(errorKeys[errorCode]!));
      } else {
        // Fallback to generic error key
        const errorKey = getZodErrorKey(result.error);
        setError(t(errorKey));
      }
    }
  }, [schema, value, setValue, setError, errorKeys, t]);

  const handleChange = useCallback(
    (newValue: T) => {
      setValue(newValue);
      // Clear error on change
      setError("");
    },
    [setValue, setError],
  );

  return { onChange: handleChange, onBlur: handleBlur };
};

/**
 * Helper to map common validation error keys
 * Reusable mappings for standard field types
 */
export const ERROR_KEY_MAPPINGS = {
  imageName: {
    too_small: "validation.imageName.empty",
    too_big: "validation.imageName.tooLong",
  },
  description: {
    too_small: "validation.description.empty",
    too_big: "validation.description.tooLong",
  },
  magnification: {
    too_small: "validation.magnification.tooSmall",
    too_big: "validation.magnification.tooLarge",
  },
} as const;
