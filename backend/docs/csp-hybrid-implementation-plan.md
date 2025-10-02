# Hybrid CSP Approach Implementation Plan

**Goal:** Implement hash-based CSP for scripts while keeping `'unsafe-inline'` for styles (Material-UI requirement)

## Overview

This plan implements a hybrid Content Security Policy approach:

- **Scripts**: Hash-based CSP (secure against XSS)
- **Styles**: `'unsafe-inline'` (required for Material-UI/Emotion CSS-in-JS)

## Why Hybrid?

1. **Material-UI uses Emotion** which injects styles dynamically at runtime
2. **Cannot pre-calculate hashes** for runtime-generated styles
3. **Scripts are static** at build time and can use hashes
4. **80% security benefit** with 20% of complexity

## Phase 1: Frontend Build Script (Generate CSP Hashes)

### 1.1 Create Hash Generation Script

Create `frontend/scripts/generate-csp-hashes.js`:

```javascript
import { readFileSync, writeFileSync } from 'fs';
import { createHash } from 'crypto';
import { load } from 'cheerio';

const indexHtmlPath = 'dist/index.html';
const outputPath = 'dist/csp-hashes.json';

// Read the built index.html
const html = readFileSync(indexHtmlPath, 'utf-8');
const $ = load(html);

// Extract inline scripts (no src attribute)
const scriptHashes = [];
$('script:not([src])').each((_, element) => {
  const content = $(element).html();
  if (content && content.trim()) {
    const hash = createHash('sha256')
      .update(content)
      .digest('base64');
    scriptHashes.push(`sha256-${hash}`);
  }
});

// Output to JSON
const output = {
  version: new Date().toISOString(),
  scriptHashes,
};

writeFileSync(outputPath, JSON.stringify(output, null, 2));
console.log(`✅ Generated ${scriptHashes.length} script hashes`);
console.log(`📄 Output: ${outputPath}`);
```

### 1.2 Install Dependencies

```bash
cd frontend
npm install --save-dev cheerio
```

### 1.3 Update package.json

Modify the build script:

```json
{
  "scripts": {
    "build": "tsc && vite build && node scripts/generate-csp-hashes.js"
  }
}
```

### 1.4 Update Azure Upload Script

Ensure `scripts/upload-to-azure.js` (or equivalent) includes `csp-hashes.json` in the upload:

```javascript
const filesToUpload = [
  'index.html',
  'csp-hashes.json',  // Add this
  // ... other files
];
```

## Phase 2: Backend CSP Manager

### 2.1 Create CSP Manager

Create `backend/app/middleware/headers/csp_manager.py`:

```python
"""
CSP Manager for dynamic Content Security Policy header generation.
Loads script hashes from frontend build artifacts in blob storage.
"""

from typing import Optional, List
from app.blob.manager import blob_storage_manager
from app.blob.exceptions import BlobNotFoundError
import json


class CSPManager:
    """
    Manages Content Security Policy headers with dynamic script hashes.
    """

    _script_hashes: List[str] = []
    _csp_header: Optional[str] = None
    _container_name: str = "frontend"
    _hashes_file: str = "csp-hashes.json"

    @classmethod
    def configure(cls, container_name: str, hashes_file: str = "csp-hashes.json"):
        """Configure CSP manager with blob storage paths."""
        cls._container_name = container_name
        cls._hashes_file = hashes_file

    @classmethod
    async def load_hashes(cls) -> bool:
        """
        Load script hashes from blob storage and build CSP header.

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            storage = blob_storage_manager.get_client()
            content = await storage.download_blob(cls._container_name, cls._hashes_file)
            data = json.loads(content.decode('utf-8'))

            cls._script_hashes = data.get('scriptHashes', [])
            cls._build_csp_header()

            print(f"✅ Loaded {len(cls._script_hashes)} script hashes for CSP")
            return True

        except BlobNotFoundError:
            print(f"⚠️  CSP hashes file not found: {cls._hashes_file}")
            cls._use_fallback_csp()
            return False

        except Exception as e:
            print(f"❌ Failed to load CSP hashes: {e}")
            cls._use_fallback_csp()
            return False

    @classmethod
    def _build_csp_header(cls):
        """Build CSP header string from loaded hashes."""
        # Start with base directives
        script_src = "'self'"

        # Add hashes for inline scripts
        if cls._script_hashes:
            script_src += " " + " ".join(f"'{h}'" for h in cls._script_hashes)

        # Build full CSP
        cls._csp_header = (
            f"default-src 'self'; "
            f"script-src {script_src}; "
            f"style-src 'self' 'unsafe-inline'; "  # Material-UI requirement
            f"img-src 'self' data: blob:; "
            f"font-src 'self' data:; "
            f"connect-src 'self';"
        )

    @classmethod
    def _use_fallback_csp(cls):
        """Use fallback CSP when hashes cannot be loaded."""
        print("⚠️  Using fallback CSP with 'unsafe-inline' for scripts")
        cls._csp_header = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self';"
        )

    @classmethod
    def get_csp_header(cls) -> str:
        """Get the current CSP header value."""
        if cls._csp_header is None:
            cls._use_fallback_csp()
        return cls._csp_header

    @classmethod
    async def refresh(cls) -> bool:
        """Refresh CSP hashes from blob storage."""
        print("🔄 Refreshing CSP hashes...")
        return await cls.load_hashes()
```

### 2.2 Update Headers Middleware

Modify `backend/app/middleware/headers/headers.py`:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from app.middleware.headers.presets import PRESETS
from app.middleware.headers.header_mapping import PARAM_TO_HEADER
from app.middleware.headers.csp_manager import CSPManager


class HeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, preset: str = None, **custom_headers):
        headers = PRESETS.get(preset, {}).copy() if preset else {}

        for param_name, value in custom_headers.items():
            if param_name not in PARAM_TO_HEADER:
                continue
            header_name = PARAM_TO_HEADER[param_name]
            if value is None:
                headers.pop(header_name, None)
            else:
                headers[header_name] = value

        self.headers = headers
        self.use_dynamic_csp = preset == "strict"  # Only for strict preset
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        for header_name, header_value in self.headers.items():
            # Use dynamic CSP if enabled and it's the CSP header
            if header_name == "Content-Security-Policy" and self.use_dynamic_csp:
                header_value = CSPManager.get_csp_header()

            response.headers[header_name] = header_value

        return response
```

### 2.3 Update Config Lifespan

Modify `backend/app/api/config.py` to initialize CSP manager:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting lifespan startup...")

    settings = get_settings()
    # ... existing initialization ...

    # Initialize frontend service
    if settings.frontend_blob_container and settings.frontend_version_file:
        print("🔄 Initializing frontend service...")
        from app.service import FrontendService
        from app.middleware.headers.csp_manager import CSPManager

        FrontendService.configure(
            settings.frontend_blob_container, settings.frontend_version_file
        )
        await FrontendService.check_and_update_version()

        # Initialize CSP Manager
        print("🔄 Initializing CSP manager...")
        CSPManager.configure(settings.frontend_blob_container)
        await CSPManager.load_hashes()
        print("✅ CSP manager initialized successfully")

        print("✅ Frontend service initialized successfully")

    # ... rest of startup ...

    yield

    # Shutdown
    # ... existing shutdown ...
```

### 2.4 Update Frontend Version Checking

Modify `backend/app/service/frontend.py` to refresh CSP on version change:

```python
@classmethod
async def check_and_update_version(cls) -> bool:
    """
    Check if version has changed and invalidate cache if needed.

    Returns:
        True if cache was invalidated, False otherwise
    """
    try:
        new_version = await cls.get_version()

        if cls._current_version is None:
            cls._current_version = new_version
            return False

        if new_version != cls._current_version:
            print(f"🔄 Frontend version changed: {cls._current_version} → {new_version}")
            cls.invalidate_cache()
            cls._current_version = new_version

            # Refresh CSP hashes when version changes
            from app.middleware.headers.csp_manager import CSPManager
            await CSPManager.refresh()

            return True

        return False
    except Exception as e:
        print(f"⚠️  Failed to check frontend version: {e}")
        return False
```

## Phase 3: Testing & Validation

### 3.1 Build and Test

1. Build frontend:

   ```bash
   cd frontend
   npm run build
   ```

2. Verify `dist/csp-hashes.json` exists

3. Check hash format:

   ```bash
   cat dist/csp-hashes.json
   ```

### 3.2 Browser Testing

1. Open browser DevTools Console
2. Check for CSP violations (should be none)
3. Verify Network tab shows CSP header with hashes

### 3.3 Version Update Test

1. Deploy new frontend version
2. Verify backend detects version change
3. Confirm CSP hashes are refreshed

### 3.4 Error Handling

Test edge cases:

- Missing `csp-hashes.json` → should fallback to `'unsafe-inline'`
- Invalid JSON → should fallback gracefully
- No inline scripts → should work with empty hash list

## Expected Results

### Current CSP (after my earlier fix)

```text
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
```

### After Hybrid Implementation

```text
script-src 'self' 'sha256-abc123...' 'sha256-def456...';
style-src 'self' 'unsafe-inline';
```

## Security Benefits

- ✅ **Scripts protected by hashes** - blocks unauthorized inline scripts
- ✅ **No script injection attacks** - only pre-approved scripts execute
- ✅ **Styles remain functional** - Material-UI works as expected
- ✅ **Automatic updates** - hashes refresh with each deployment
- ✅ **Graceful degradation** - falls back if hashes unavailable

## Maintenance

1. **No manual hash management** - automated in build process
2. **Version-aware** - CSP updates when frontend updates
3. **Monitoring** - logs show hash loading status
4. **Fallback safety** - never breaks the application

## Future Enhancements

1. **CSP Reporting**: Add `report-uri` directive to monitor violations
2. **Stricter Policies**: Add `object-src 'none'`, `base-uri 'self'`
3. **Nonce Support**: If Vite adds nonce injection support in future
4. **External Scripts**: Add specific hashes/domains for CDN scripts if needed
