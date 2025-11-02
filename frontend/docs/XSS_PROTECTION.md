# XSS Protection Guide

This guide explains how to use the comprehensive XSS (Cross-Site Scripting) protection features added to the Nachet frontend application.

## Overview

XSS attacks occur when malicious scripts are injected into web pages and executed by users' browsers. Our validation system now includes comprehensive protection against these attacks using a **security-first approach that rejects potentially dangerous input** rather than attempting complex sanitization.

## Key Principles

1. **Reject Dangerous Input Early** - Block HTML and script content at input validation
2. **Escape Output, Not Input** - Store original data and escape when rendering
3. **Validate All User Input** - Use strict validation schemas that reject unsafe content
4. **Use Content Security Policy** - Add an extra layer of protection
5. **Never Trust User Data** - Always validate before processing or rendering
6. **Fail-Safe Defaults** - When in doubt, reject the input

## Available Functions

### HTML Escaping

```typescript
import {
  escapeHtml,
  escapeHtmlAttribute,
  escapeJavaScript,
} from "./validation";

// Escape HTML special characters
const safeHtml = escapeHtml('<script>alert("xss")</script>');
// Result: &lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;

// Escape HTML attributes
const safeAttr = escapeHtmlAttribute("onclick=\"alert('xss')\"");
// Result: onclick=&#x27;alert(&#x27;xss&#x27;)&#x27;

// Escape JavaScript strings
const safeJs = escapeJavaScript('"; alert("xss"); "');
// Result: \\u0022; alert(\\u0022xss\\u0022); \\u0022
```

### URL Sanitization

```typescript
import { sanitizeUrl } from "./validation";

// Safe URLs are allowed
const httpUrl = sanitizeUrl("https://example.com"); // ✅ Returns: 'https://example.com'
const relativeUrl = sanitizeUrl("/path/to/page"); // ✅ Returns: '/path/to/page'

// Dangerous URLs are blocked
const jsUrl = sanitizeUrl('javascript:alert("xss")'); // ❌ Returns: null
const dataUrl = sanitizeUrl('data:text/html,<script>alert("xss")</script>'); // ❌ Returns: null
```

### Validation Schemas

Use these schemas for form validation - they now **reject HTML content** instead of sanitizing:

```typescript
import {
  safeTextSchema,
  safeUserInputSchema,
  safeUrlSchema,
  safeImageLabelSchema,
  safeHtmlSchema,
  containsHtml,
} from "./validation";

// Validate user text input (rejects HTML)
try {
  const safeText = safeTextSchema.parse(userInput);
  // Use safeText - it's been validated and trimmed
} catch (error) {
  // Handle validation error - may include HTML rejection
}

// Validate URLs
try {
  const safeUrl = safeUrlSchema.parse(userUrl);
  // Use safeUrl - dangerous URLs are rejected
} catch (error) {
  // Handle invalid/unsafe URL
}

// Check for HTML content before processing
if (containsHtml(userInput)) {
  throw new Error("HTML content is not allowed - please use plain text only");
}

// Safe HTML schema now rejects any HTML input
try {
  const plainText = safeHtmlSchema.parse(userContent);
  // Only plain text is accepted
} catch (error) {
  // HTML content is rejected with clear error message
}
```

## Usage Examples

### React Components

```typescript
import { escapeHtml, escapeHtmlAttribute, containsHtml } from './validation';

// ✅ SAFE: Properly escaped user content
const SafeUserContent = ({ userText, userTitle }) => {
  // Check for HTML before rendering
  if (containsHtml(userText)) {
    return <div className="error">HTML content is not allowed</div>;
  }

  return (
    <div
      title={escapeHtmlAttribute(userTitle)}
      dangerouslySetInnerHTML={{ __html: escapeHtml(userText) }}
    />
  );
};

// ✅ BETTER: Reject HTML at input level
const SecureUserContent = ({ userText, userTitle }) => (
  <div title={escapeHtmlAttribute(userTitle)}>
    {escapeHtml(userText)}
  </div>
);
```

### Form Handling

```typescript
import { safeUserInputSchema, containsHtml } from "./validation";

const handleFormSubmit = (formData) => {
  try {
    // Pre-check for HTML content
    if (containsHtml(formData.comment) || containsHtml(formData.title)) {
      throw new Error("HTML content is not allowed in form inputs");
    }

    // Validate all user inputs (will also reject HTML)
    const safeComment = safeUserInputSchema.parse(formData.comment);
    const safeTitle = safeUserInputSchema.parse(formData.title);

    // Now safe to use in your application
    submitData({ comment: safeComment, title: safeTitle });
  } catch (error) {
    // Show validation error to user
    setError(error.message || "Please check your input for invalid characters");
  }
};
```

### Template Rendering

```typescript
import { html } from "./xss-utils";

// Safe template literal helper
const renderUserCard = (name, bio) => html`
  <div class="user-card">
    <h3>${name}</h3>
    <p>${bio}</p>
  </div>
`;
// All variables are automatically escaped
```

## Content Security Policy

Set up CSP headers to add an extra layer of protection:

```typescript
import { generateCSP, setupCSP } from "./xss-utils";

// For Express.js
app.use(setupCSP().expressMiddleware);

// For client-side (add to HTML head)
const cspMeta = setupCSP().metaTag;
```

## Testing XSS Protection

Use the provided test patterns to verify your protection:

```typescript
import { testXSSProtection, XSSTestPatterns } from "./xss-utils";

// Run comprehensive XSS tests
testXSSProtection();

// Test specific patterns
XSSTestPatterns.forEach((pattern) => {
  const escaped = escapeHtml(pattern);
  console.log({ original: pattern, escaped });
});
```

## Common XSS Attack Vectors

Our protection handles these attack types:

1. **Script Injection**: `<script>alert('xss')</script>`
2. **Event Handlers**: `<img onerror="alert('xss')" src="x">`
3. **JavaScript URLs**: `javascript:alert('xss')`
4. **Data URLs**: `data:text/html,<script>alert('xss')</script>`
5. **CSS Injection**: `<style>body{background:url(javascript:alert('xss'))}</style>`
6. **HTML Attributes**: `<div onclick="alert('xss')">Click me</div>`

## Best Practices

### ✅ DO

- Always validate user input before processing
- Reject HTML content at input validation using `containsHtml()`
- Use validation schemas for all user inputs
- Escape output at the last possible moment before rendering
- Set up Content Security Policy headers
- Test your XSS protection regularly
- Use plain text input fields when HTML is not needed

### ❌ DON'T

- Never trust user input
- Don't attempt to sanitize HTML - reject it instead
- Don't use `dangerouslySetInnerHTML` without proper validation
- Don't rely only on client-side validation
- Don't concatenate user input directly into HTML strings
- Don't use complex sanitization libraries when simple rejection works

## Migration Guide

### Updating Existing Code

1. **Replace HTML sanitization with rejection**:

   ```typescript
   // Old approach (sanitization)
   const clean = stripDangerousHtml(userInput);

   // New approach (rejection)
   if (containsHtml(userInput)) {
     throw new Error("HTML content is not allowed");
   }
   const safe = userInput;
   ```

2. **Update form validation**:

   ```typescript
   // Old
   const isValid = userInput.length > 0 && userInput.length < 100;

   // New - includes HTML rejection
   const validated = safeUserInputSchema.parse(userInput);
   ```

3. **Secure content handling**:

   ```typescript
   // Old - attempted sanitization
   const safeContent = stripDangerousHtml(userContent);

   // New - reject HTML entirely
   if (containsHtml(userContent)) {
     throw new Error("HTML content is not allowed - please use plain text");
   }
   const safeContent = userContent;
   ```

4. **Update error messages**:

   ```typescript
   // Old
   catch (error) {
     setError('Invalid input');
   }

   // New - more specific
   catch (error) {
     if (error.message.includes('HTML')) {
       setError('HTML content is not allowed - please use plain text only');
     } else {
       setError('Invalid input characters detected');
     }
   }
   ```

## Additional Resources

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [Content Security Policy Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [HTML Escaping Best Practices](<https://www.owasp.org/index.php/XSS_(Cross_Site_Scripting)_Prevention_Cheat_Sheet>)
- [Input Validation vs Sanitization](https://owasp.org/www-community/Injection_Theory) - Why rejection is often better than sanitization
- [Fail-Safe Defaults Principle](https://owasp.org/www-pdf-archive/OWASP_Top_10_2010.pdf) - OWASP guidance on secure defaults
