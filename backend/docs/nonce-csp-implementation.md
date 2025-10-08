# Nonce-Based Content Security Policy (CSP) Implementation

**Status:** ✅ Phase 1 Complete
**Last Updated:** 2025-10-02

---

## Overview

This document describes the implementation of a nonce-based Content Security Policy (CSP) system that provides robust XSS protection while maintaining full compatibility with Material-UI/Emotion's runtime style injection.

### Problem Statement

The application uses Material-UI with Emotion CSS-in-JS, which dynamically injects `<style>` tags at runtime. A strict CSP policy with `default-src 'self'` blocks these inline styles, causing CSP violations:

```text
Refused to apply inline style because it violates the following Content Security Policy directive: "default-src 'self'"
```

### Solution

Implement per-request cryptographic nonces that allow specific inline scripts and styles while blocking unauthorized code injection.

---

## Architecture

### Request Flow

```text
1. Client requests index.html
   ↓
2. HeadersMiddleware generates unique nonce (32 bytes random)
   ↓
3. Nonce stored in request.state.csp_nonce
   ↓
4. HeadersMiddleware adds CSP header with nonce:
   Content-Security-Policy: script-src 'self' 'nonce-{random}'; style-src 'self' 'nonce-{random}';
   ↓
5. FrontendService retrieves index.html from blob storage
   ↓
6. FrontendService injects nonce into HTML:
   - Replaces __CSP_NONCE__ with actual nonce
   - Adds <meta property="csp-nonce" content="{nonce}">
   ↓
7. Browser receives HTML with nonces matching CSP header
   ↓
8. Emotion reads nonce from meta tag
   ↓
9. Material-UI injects styles with nonce attribute
   ↓
10. ✅ Browser allows styles (nonce matches CSP header)
```

---

## Implementation Details

### Backend Components

#### 1. CSP Nonce Manager

**File:** `backend/app/middleware/headers/csp_nonce_manager.py`

**Purpose:** Generate cryptographically secure nonces and build CSP headers

**Key Functions:**

- `generate_nonce(length=32)` - Creates base64-encoded random nonce
- `build_csp_header(nonce, include_report_uri=False)` - Constructs CSP header string
- `extract_nonce_from_request(request)` - Retrieves nonce from request state

**Security:**

- Uses `secrets.token_urlsafe()` for cryptographic randomness
- Default 32 bytes = 256 bits of entropy
- Base64-encoded for URL safety

#### 2. Headers Middleware

**File:** `backend/app/middleware/headers/headers.py`

**Changes:**

- Added `use_csp_nonce` parameter (default: `True`)
- Generates unique nonce per request
- Stores nonce in `request.state.csp_nonce`
- Dynamically replaces CSP header with nonce-based version

**Example:**

```python
# Before
Content-Security-Policy: default-src 'self';

# After
Content-Security-Policy: script-src 'self' 'nonce-8x7g2k...'; style-src 'self' 'nonce-8x7g2k...';
```

#### 3. Frontend Service

**File:** `backend/app/service/frontend.py`

**Changes:**

- Added `csp_nonce` parameter to `get_file()` method
- New `_inject_nonce_into_html()` static method
- Replaces `__CSP_NONCE__` placeholder in HTML
- Adds `<meta property="csp-nonce">` tag for client-side access

**Caching Strategy:**

- Base HTML cached without nonce (shared across requests)
- Nonce injection happens at request time (not cached)
- Prevents stale nonces from being served

#### 4. API Routes

**File:** `backend/app/api/routes.py`

**Changes:**

- Updated `serve_frontend_root()` to pass nonce to FrontendService
- Updated `serve_frontend_static()` to pass nonce for fallback index.html
- Extracts nonce from `request.state.csp_nonce`

---

### Frontend Components

#### 1. Vite Configuration

**File:** `frontend/vite.config.ts`

**Changes:**

```typescript
html: {
  cspNonce: "__CSP_NONCE__"  // Placeholder replaced by backend
}
```

**Effect:**

- Vite adds `nonce="__CSP_NONCE__"` to all `<script>` and `<link>` tags during build
- Backend replaces placeholder with actual nonce at request time

#### 2. Emotion Cache

**File:** `frontend/src/common/emotionCache.ts`

**Purpose:** Configure Emotion to use CSP nonces for Material-UI styles

**Key Functions:**

- `getCSPNonce()` - Reads nonce from `<meta property="csp-nonce">`
- `createEmotionCache()` - Creates cache with nonce support

**Emotion Configuration:**

```typescript
createCache({
  key: "mui-style",
  nonce: getCSPNonce(),  // Nonce from meta tag
  prepend: true          // Insert at <head> start
})
```

#### 3. App Entry Point

**File:** `frontend/src/main.tsx`

**Changes:**

- Import `CacheProvider` from `@emotion/react`
- Create Emotion cache with nonce
- Wrap `<App>` with `<CacheProvider value={emotionCache}>`

**Effect:**

- All Material-UI components use nonce-enabled cache
- Injected styles include `nonce` attribute
- Browser allows styles matching CSP header

---

## Security Properties

### XSS Protection

✅ **Blocks inline script injection**

- Only scripts with matching nonce execute
- Attackers cannot predict nonces (cryptographically random)

✅ **Blocks inline style injection**

- Only styles with matching nonce apply
- Prevents CSS-based data exfiltration attacks

✅ **Per-request nonces**

- Each request gets unique nonce
- Cannot replay nonces across requests
- Prevents CSRF-style nonce reuse

✅ **No `unsafe-inline`**

- Strongest CSP protection level
- Material-UI works without weakening CSP

### CSP Directives

Current CSP header includes:

```text
default-src 'self'
script-src 'self' 'nonce-{random}'
style-src 'self' 'nonce-{random}'
img-src 'self' data: blob:
font-src 'self' data:
connect-src 'self'
object-src 'none'
base-uri 'self'
form-action 'self'
```

---

## Testing

### Verification Steps

1. **Build Frontend**

   ```bash
   cd frontend
   npm run build
   ```

2. **Verify Nonce Placeholders**

   ```bash
   cat dist/index.html | grep __CSP_NONCE__
   ```

   Should show:

   ```html
   <script nonce="__CSP_NONCE__">
   <link nonce="__CSP_NONCE__">
   <meta property="csp-nonce" nonce="__CSP_NONCE__">
   ```

3. **Start Backend**

   ```bash
   cd backend
   uv run hypercorn -b :8080 app/main:app
   ```

4. **Browser Testing**
   - Open DevTools → Console
   - Navigate to application
   - Check for CSP violations (should be zero)
   - Verify Material-UI styles render correctly

5. **Inspect Headers**
   - DevTools → Network → Select document
   - Check Response Headers for:

     ```text
     Content-Security-Policy: script-src 'self' 'nonce-...'; style-src 'self' 'nonce-...';
     ```

6. **Inspect HTML**
   - DevTools → Elements → View page source
   - Verify nonce values match across:
     - `<script nonce="abc123">`
     - `<link nonce="abc123">`
     - `<meta property="csp-nonce" content="abc123">`
     - CSP header

7. **Test Material-UI**
   - Verify all MUI components render correctly
   - Check for dynamic styles in `<head>`
   - Styles should have `nonce` attributes

### Expected Results

**Before (CSP violations):**

```text
❌ Refused to apply inline style because it violates CSP directive: "default-src 'self'"
❌ Refused to execute inline script because it violates CSP directive
```

**After (No violations):**

```text
✅ CSP nonce found, creating Emotion cache with nonce support
✅ All Material-UI styles render correctly
✅ No CSP errors in console
```

---

## Troubleshooting

### Problem: "CSP nonce not found in meta tag"

**Symptoms:**

- Console warning: `⚠️ CSP nonce not found in meta tag`
- Material-UI styles blocked

**Causes:**

1. Backend not replacing `__CSP_NONCE__` placeholder
2. Frontend served from wrong source (not through backend)

**Solutions:**

- Verify backend `FrontendService._inject_nonce_into_html()` is called
- Check `request.state.csp_nonce` has value
- Ensure frontend served via backend routes, not Vite dev server

### Problem: CSP Violations Persist

**Symptoms:**

- CSP errors still appear in console
- Nonce values don't match

**Causes:**

1. Cached HTML with old/no nonce
2. Middleware order incorrect
3. External scripts without nonces

**Solutions:**

- Clear browser cache and hard reload
- Verify `HeadersMiddleware` runs before response
- Check CSP header and HTML nonce values match
- Add external domains to CSP if needed

### Problem: Styles Not Applying

**Symptoms:**

- Material-UI components unstyled
- No CSP errors

**Causes:**

1. Emotion cache not using nonce
2. CacheProvider missing
3. Nonce not passed to Emotion

**Solutions:**

- Verify `CacheProvider` wraps `<App>`
- Check `createEmotionCache()` returns cache with nonce
- Inspect `<style>` tags for `nonce` attribute

---

## Performance Considerations

### Nonce Generation

- **Cost:** ~1μs per nonce (negligible)
- **Frequency:** Once per request
- **Impact:** Minimal overhead

### HTML Injection

- **Cost:** String replacement on cached HTML
- **Frequency:** Once per request
- **Optimization:** Base HTML cached, only nonce injection on each request
- **Impact:** <1ms per request

### Caching Strategy

- **Base HTML:** Cached in memory (shared across requests)
- **Nonce-injected HTML:** Generated per request (not cached)
- **Static Assets:** Cached normally (no nonce injection needed)

---

## Future Enhancements (Phase 2)

### CSP Reporting

- Add `report-uri /api/csp-report` directive
- Log CSP violations
- Alert on repeated attack attempts

### Input Sanitization

- Server-side XSS pattern detection
- Reject requests with suspicious payloads
- Additional defense layer

### Stricter Policies

- Add `upgrade-insecure-requests` directive
- Implement `Trusted Types` API
- Enable `require-trusted-types-for 'script'`

---

## References

- [Vite CSP Documentation](https://vite.dev/guide/features.html#content-security-policy-csp)
- [Emotion Cache API](https://emotion.sh/docs/@emotion/cache)
- [MDN CSP Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [OWASP XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)

---

## Changelog

### 2025-10-02 - Phase 1 Complete

- ✅ Implemented nonce generation backend
- ✅ Updated middleware for dynamic CSP headers
- ✅ Added HTML nonce injection
- ✅ Configured Vite with CSP nonce support
- ✅ Integrated Emotion cache with nonces
- ✅ Tested and verified no CSP violations
