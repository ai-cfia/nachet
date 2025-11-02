# i18n Reference Guide for Nachet Frontend

**Last Updated:** 2025-11-02
**Status:** ✅ Complete (100% coverage)
**Languages:** English (en), French (fr)

## Overview

The Nachet frontend uses **i18next** and **react-i18next** for internationalization. All user-facing strings are translated into English and French, with proper separation between UI translations and developer-facing logs.

## Quick Start

### Adding Translations to a Component

**Functional Component:**

```typescript
import { useTranslation } from "react-i18next";

function MyComponent() {
  const { t } = useTranslation("namespace");

  return <button>{t("key.path")}</button>;
}
```

**Class Component:**

```typescript
import { withTranslation, WithTranslation } from "react-i18next";

interface Props extends WithTranslation {
  // other props
}

class MyComponent extends Component<Props> {
  render() {
    const { t } = this.props;
    return <button>{t("key.path")}</button>;
  }
}

const MyComponentWithTranslation = withTranslation()(MyComponent);
MyComponentWithTranslation.displayName = "MyComponent";
export default MyComponentWithTranslation;
```

**Multiple Namespaces:**

```typescript
const { t } = useTranslation("popups");
const { t: tCommon } = useTranslation("common");
const { t: tErrors } = useTranslation("errors");

return (
  <div>
    <h1>{t("title")}</h1>
    <button>{tCommon("actions.save")}</button>
    <p>{tErrors("auth.signInRequired")}</p>
  </div>
);
```

**Interpolation:**

```typescript
// Translation: "Hello {{name}}, you have {{count}} messages"
t("greeting", { name: "John", count: 5 })
// Output: "Hello John, you have 5 messages"
```

## Translation File Structure

```text
frontend/src/locales/
├── en/                          # English translations
│   ├── common.ts               # Shared terms (actions, status, form)
│   ├── header.ts               # Navbar, AppBar
│   ├── footer.ts               # Footer component
│   ├── popups.ts               # All popup/dialog components
│   ├── main.ts                 # Main app UI (MicroscopeFeed, etc.)
│   ├── validation.ts           # Zod validation error messages
│   └── errors.ts               # User-facing error messages
└── fr/                          # French translations
    └── (same structure as en/)
```

## Translation Namespaces

### 1. Common (`common.ts`)

**Usage:** Shared terms used across multiple components

```typescript
const { t } = useTranslation("common");
```

**Keys:**

- `actions.*` - Button labels (save, cancel, close, delete, edit, add, remove, confirm, dismiss, etc.)
- `status.*` - Status messages (loading, processing, complete, success, error, warning, info)
- `form.*` - Form labels (required, optional)

**Example:**

```typescript
<Button>{t("common:actions.save")}</Button>
<span>{t("common:status.loading")}</span>
```

### 2. Header (`header.ts`)

**Usage:** Navbar and AppBar components

```typescript
const { t } = useTranslation("header");
```

**Keys:**

- `navbar.*` - Sign in/out buttons, greetings
- `appBar.*` - Application title, language toggle

### 3. Footer (`footer.ts`)

**Usage:** Footer component

```typescript
const { t } = useTranslation("footer");
```

**Keys:**

- `developedBy` - Developer credit
- `connected` / `disconnected` - Connection status
- `version` - Version label
- `oid` - OID label
- `canadaLogoAlt` - Canada logo alt text

### 4. Popups (`popups.ts`)

**Usage:** All popup/dialog components

```typescript
const { t } = useTranslation("popups");
```

**Keys:**

- `auth.*` - Authentication popup
- `creativeCommons.*` - Creative Commons agreement
- `deviceInfo.*` - Device information popup
- `modelInfo.*` - Model selection popup
- `saveCapture.*` - Save capture popup
- `uploadImage.*` - Upload image popup
- `createDirectory.*` - Create/edit directory popup
- `deleteDirectory.*` - Delete directory popup
- `batchUpload.*` - Batch upload popup
- `feedback.*` - Feedback form
- `registrationStatus.*` - Registration status popup
- `switchDevice.*` - Switch device popup

### 5. Main (`main.ts`)

**Usage:** Main application components

```typescript
const { t } = useTranslation("main");
```

**Keys:**

- `microscopeFeed.*` - Microscope feed controls, buttons, errors
- `classificationResults.*` - Results display
- `imageCache.*` - Capture labels, workflow tooltips
- `storageDirectory.*` - Directory list

### 6. Validation (`validation.ts`)

**Usage:** Zod validation error messages

```typescript
import { getZodErrorKey } from "@common/zodErrorMap";
const { t } = useTranslation("validation");

const validation = schema.safeParse(value);
if (!validation.success) {
  setError(t(getZodErrorKey(validation.error)));
}
```

**Keys:**

- `string.*` - String validation errors (min, max, required, etc.)
- `number.*` - Number validation errors
- `array.*` - Array validation errors
- `custom.*` - Custom validation errors

### 7. Errors (`errors.ts`)

**Usage:** User-facing error messages (alerts, toasts, error boundaries)

```typescript
const { t } = useTranslation("errors");
```

**Keys:**

- `auth.*` - Authentication errors (signInRequired, inProgress, etc.)
- `directory.*` - Directory selection errors
- `inference.*` - Inference processing errors
- `queue.*` - Queue full errors
- `registration.*` - Registration check errors
- `storage.*` - Azure storage errors
- `save.*` - Image save errors
- `boundary.*` - Error boundary UI strings

## Critical Rules

### ✅ DO TRANSLATE (User-Facing UI)

- `alert()` messages displayed to users
- Dialog/popup content
- Button labels
- Error messages shown in UI components
- Toast/Snackbar notifications
- Form validation errors displayed to users
- Tooltips and ARIA labels
- Empty states and no-results messages

### ❌ KEEP IN ENGLISH (Server/Logging)

- `console.log()`, `console.error()`, `console.warn()` messages
- `errorLogger.*` calls (logs sent to backend)
- `throw new Error()` messages
- Error objects in API requests
- Debug information
- Stack traces

### Dual-Messaging Pattern

**Pattern:** Separate user-facing translations from developer/server logs

```typescript
// ✅ CORRECT
const { t } = useTranslation("errors");

// User sees translated message
alert(t("errors.uploadFailed"));

// Console/logs stay in English
console.error("File upload failed: network timeout", error);

// Server logs in English
errorLogger.logError("Authentication failed", error);
```

**Anti-Patterns to Avoid:**

```typescript
// ❌ WRONG: Translated string sent to console
const errorMsg = t("errors.uploadFailed");
console.error(errorMsg);

// ❌ WRONG: Translated string sent to server
errorLogger.logError(t("errors.networkError"), error);

// ❌ WRONG: Translated error thrown
throw new Error(t("errors.invalidData"));
```

## Component Coverage

### Translated Components (27/27 - 100%)

#### Phase 1: Infrastructure

- ✅ i18n configuration
- ✅ Translation file structure

#### Phase 2: Header & Footer (3 components)

- ✅ Navbar
- ✅ AppBar
- ✅ Footer

#### Phase 3: Popups & Dialogs (10 components)

- ✅ AuthPopup
- ✅ CreativeCommonsPopup
- ✅ DeviceInfoPopup
- ✅ ModelPopup
- ✅ SaveCapturePopup
- ✅ UploadPopup
- ✅ CreateDirectoryPopup
- ✅ DeleteDirectoryPopup
- ✅ BatchUploadPopupView
- ✅ FeedbackForm

#### Phase 4: Main Application (7 components)

- ✅ MicroscopeFeedControlsView
- ✅ MicroscopeFeed
- ✅ ClassificationResults
- ✅ ImageCache
- ✅ StorageDirectoryView
- ✅ (Batch upload UI covered in Phase 3)

#### Phase 5: Validation (3 components)

- ✅ BatchUploadPopupContainer (validation)
- ✅ CreateDirectoryPopup (validation)
- ✅ SaveCapturePopup (validation)

#### Phase 6: Finalization (7 components)

- ✅ body.tsx (11 alert messages)
- ✅ ErrorBoundary (6 UI strings)
- ✅ RegistrationStatusPopup (6 strings)
- ✅ BatchUploadPopupContainer (2 alerts)
- ✅ SaveCapturePopup (1 alert)
- ✅ ApiAction (1 button)
- ✅ SwitchDevicePopup (1 title)

## Adding New Translations

### Step 1: Add Translation Keys

**English (`src/locales/en/namespace.ts`):**

```typescript
export const namespace = {
  myFeature: {
    title: "My Feature",
    description: "This is a description",
    button: "Click Me",
  },
} as const;

export default namespace;
```

**French (`src/locales/fr/namespace.ts`):**

```typescript
export const namespace = {
  myFeature: {
    title: "Ma fonctionnalité",
    description: "Ceci est une description",
    button: "Cliquez ici",
  },
} as const;

export default namespace;
```

### Step 2: Register Namespace (if new)

**In `src/i18n.ts`:**

```typescript
import enNamespace from "./locales/en/namespace";
import frNamespace from "./locales/fr/namespace";

const resources = {
  en: {
    // ... existing
    namespace: enNamespace,
  },
  fr: {
    // ... existing
    namespace: frNamespace,
  },
} as const;
```

### Step 3: Use in Component

```typescript
import { useTranslation } from "react-i18next";

function MyComponent() {
  const { t } = useTranslation("namespace");

  return (
    <div>
      <h1>{t("myFeature.title")}</h1>
      <p>{t("myFeature.description")}</p>
      <button>{t("myFeature.button")}</button>
    </div>
  );
}
```

## Zod Validation Integration

### Pattern: Component-Level Interception

**Helper Functions (`src/common/zodErrorMap.ts`):**

```typescript
// Maps Zod error codes to translation keys
getZodErrorKey(error: z.ZodError): string

// Extracts interpolation values (min, max, etc.)
getZodErrorValues(error: z.ZodError): Record<string, unknown>
```

**Usage:**

```typescript
import { getZodErrorKey } from "@common/zodErrorMap";
import { useTranslation } from "react-i18next";

function MyFormComponent() {
  const { t } = useTranslation("validation");

  const handleSubmit = () => {
    const validation = schema.safeParse(value);
    if (!validation.success) {
      // Translate the error using helper function
      setError(t(getZodErrorKey(validation.error)));
      return;
    }
    // Continue with valid data...
  };
}
```

## Language Switching

**Current Language:**

```typescript
import i18n from "./i18n";

const currentLanguage = i18n.language; // "en" or "fr"
```

**Change Language:**

```typescript
import i18n from "./i18n";

i18n.changeLanguage("fr"); // Switch to French
i18n.changeLanguage("en"); // Switch to English
```

**Language Persistence:**

- Language preference is automatically saved to `localStorage`
- Key: `i18nextLng`
- Browser language is detected on first visit
- Fallback language: English (en)

## Configuration

**File:** `src/i18n.ts`

```typescript
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    supportedLngs: ["en", "fr"],
    defaultNS: "common",
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "i18nextLng",
    },
    interpolation: {
      escapeValue: false, // React already escapes by default
    },
    debug: false, // Set to true for debugging
  });
```

## Testing Translations

### Build Verification

```bash
cd frontend
npm run build
```

**Expected output:**

- ✅ Prettier formatting passed
- ✅ ESLint passed (max-warnings 0)
- ✅ TypeScript compilation passed
- ✅ Vite build successful

### Manual Testing

1. **Switch Languages:**
   - Click language toggle in AppBar (EN/FR)
   - Verify all UI strings update

2. **Test Error Messages:**
   - Trigger validation errors in forms
   - Trigger alert messages (e.g., sign in required)
   - Verify error boundary displays (if needed)

3. **Check Console:**
   - Verify console logs remain in English
   - No translated strings in console output

4. **Check localStorage:**
   - Open DevTools → Application → Local Storage
   - Verify `i18nextLng` key exists with "en" or "fr"

## Common Issues & Solutions

### Issue: Missing Translation Warning

**Symptom:** Console warning: `i18next: key 'foo.bar' not found`

**Solution:**

1. Check if key exists in translation files
2. Verify namespace is registered in `i18n.ts`
3. Check spelling and case sensitivity

### Issue: Translation Not Updating

**Symptom:** Component still shows old text after language switch

**Solution:**

1. Verify component uses `useTranslation()` hook
2. Check that component re-renders on language change
3. Clear browser cache and localStorage

### Issue: TypeScript Error on Translation Key

**Symptom:** TypeScript error: `Property 'foo' does not exist`

**Solution:**

1. Ensure translation files use `as const`
2. Rebuild TypeScript (`npm run build`)
3. Restart TypeScript server in IDE

### Issue: Class Component Not Translating

**Symptom:** Class component doesn't have `t` function

**Solution:**

1. Use `withTranslation()` HOC
2. Extend `WithTranslation` interface
3. Set `displayName` to avoid ESLint warnings

```typescript
import { withTranslation, WithTranslation } from "react-i18next";

interface Props extends WithTranslation {
  // props
}

class MyComponent extends Component<Props> {
  render() {
    const { t } = this.props;
    return <div>{t("key")}</div>;
  }
}

const MyComponentWithTranslation = withTranslation()(MyComponent);
MyComponentWithTranslation.displayName = "MyComponent";
export default MyComponentWithTranslation;
```

## File Locations Reference

**Configuration:**

- `frontend/src/i18n.ts` - i18n configuration
- `frontend/package.json` - Dependencies (i18next, react-i18next)

**Translation Files:**

- `frontend/src/locales/en/*.ts` - English translations
- `frontend/src/locales/fr/*.ts` - French translations

**Helpers:**

- `frontend/src/common/zodErrorMap.ts` - Zod error translation helpers

**Documentation:**

- `frontend/docs/I18N_IMPLEMENTATION_PLAN.md` - Implementation plan (6 phases)
- `frontend/docs/I18N_REFERENCE.md` - This reference guide

**Updated Components:**

- See "Component Coverage" section above for full list of 27 translated components

## Dependencies

```json
{
  "i18next": "^25.6.0",
  "react-i18next": "^16.2.3",
  "i18next-browser-languagedetector": "^8.0.2"
}
```

**Installation:**

```bash
npm install i18next react-i18next i18next-browser-languagedetector
```

## Best Practices

1. **Always use translation keys, never hardcode strings**

   ```typescript
   // ✅ Good
   <button>{t("actions.save")}</button>

   // ❌ Bad
   <button>Save</button>
   ```

2. **Use descriptive translation keys**

   ```typescript
   // ✅ Good
   t("auth.signInRequired")

   // ❌ Bad
   t("error1")
   ```

3. **Group related translations**

   ```typescript
   // ✅ Good
   auth: {
     signInRequired: "...",
     signInProgress: "...",
     signInFailed: "...",
   }
   ```

4. **Use interpolation for dynamic content**

   ```typescript
   // ✅ Good
   t("greeting", { name: userName })

   // ❌ Bad
   `Hello ${userName}` // Not translated
   ```

5. **Keep console logs in English**

   ```typescript
   // ✅ Good
   console.error("Failed to load user data", error);

   // ❌ Bad
   console.error(t("errors.loadFailed"));
   ```

6. **Test both languages**
   - Switch languages frequently during development
   - Verify all strings translate correctly
   - Check for layout issues with longer French text

7. **Keep translations in sync**
   - Update both EN and FR files together
   - Use same key structure in both files
   - Maintain same nesting depth

## Support

For questions or issues:

1. Check this reference guide
2. Review implementation plan: `frontend/docs/I18N_IMPLEMENTATION_PLAN.md`
3. Search codebase for examples: `grep -r "useTranslation" frontend/src/`
4. Test locally with language toggle

---

**Generated:** 2025-11-02
**i18n Version:** v1.0 (Complete)
**Coverage:** 100% (27/27 components)
