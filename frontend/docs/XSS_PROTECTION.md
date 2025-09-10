# XSS Protection Guide

This guide explains how to use the comprehensive XSS (Cross-Site Scripting) protection features added to the Nachet frontend application.

## Overview

XSS attacks occur when malicious scripts are injected into web pages and executed by users' browsers. Our validation system now includes comprehensive protection against these attacks.

## Key Principles

1. **Escape Output, Not Input** - Store original data and escape when rendering
2. **Validate All User Input** - Use strict validation schemas
3. **Use Content Security Policy** - Add an extra layer of protection
4. **Never Trust User Data** - Always sanitize before rendering

## Available Functions

### HTML Escaping

```typescript
import { escapeHtml, escapeHtmlAttribute, escapeJavaScript } from './validation';

// Escape HTML special characters
const safeHtml = escapeHtml('<script>alert("xss")</script>');
// Result: &lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;

// Escape HTML attributes  
const safeAttr = escapeHtmlAttribute('onclick="alert(\'xss\')"');
// Result: onclick=&#x27;alert(&#x27;xss&#x27;)&#x27;

// Escape JavaScript strings
const safeJs = escapeJavaScript('"; alert("xss"); "');
// Result: \\u0022; alert(\\u0022xss\\u0022); \\u0022
```

### URL Sanitization

```typescript
import { sanitizeUrl } from './validation';

// Safe URLs are allowed
const httpUrl = sanitizeUrl('https://example.com'); // ✅ Returns: 'https://example.com'
const relativeUrl = sanitizeUrl('/path/to/page'); // ✅ Returns: '/path/to/page'

// Dangerous URLs are blocked
const jsUrl = sanitizeUrl('javascript:alert("xss")'); // ❌ Returns: null
const dataUrl = sanitizeUrl('data:text/html,<script>alert("xss")</script>'); // ❌ Returns: null
```

### Validation Schemas

Use these schemas for form validation:

```typescript
import { 
  safeTextSchema, 
  safeUserInputSchema, 
  safeUrlSchema,
  safeImageLabelSchema 
} from './validation';

// Validate user text input
try {
  const safeText = safeTextSchema.parse(userInput);
  // Use safeText - it's been validated and trimmed
} catch (error) {
  // Handle validation error
}

// Validate URLs
try {
  const safeUrl = safeUrlSchema.parse(userUrl);
  // Use safeUrl - dangerous URLs are rejected
} catch (error) {
  // Handle invalid/unsafe URL
}
```

## Usage Examples

### React Components

```typescript
import { escapeHtml, escapeHtmlAttribute } from './validation';

// ✅ SAFE: Properly escaped user content
const SafeUserContent = ({ userText, userTitle }) => (
  <div 
    title={escapeHtmlAttribute(userTitle)}
    dangerouslySetInnerHTML={{ __html: escapeHtml(userText) }}
  />
);

// ❌ DANGEROUS: Never do this
const DangerousComponent = ({ userText }) => (
  <div dangerouslySetInnerHTML={{ __html: userText }} />
);
```

### Form Handling

```typescript
import { safeUserInputSchema } from './validation';

const handleFormSubmit = (formData) => {
  try {
    // Validate all user inputs
    const safeComment = safeUserInputSchema.parse(formData.comment);
    const safeTitle = safeUserInputSchema.parse(formData.title);
    
    // Now safe to use in your application
    submitData({ comment: safeComment, title: safeTitle });
  } catch (error) {
    // Show validation error to user
    setError('Please check your input for invalid characters');
  }
};
```

### Template Rendering

```typescript
import { html } from './xss-utils';

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
import { generateCSP, setupCSP } from './xss-utils';

// For Express.js
app.use(setupCSP().expressMiddleware);

// For client-side (add to HTML head)
const cspMeta = setupCSP().metaTag;
```

## Testing XSS Protection

Use the provided test patterns to verify your protection:

```typescript
import { testXSSProtection, XSSTestPatterns } from './xss-utils';

// Run comprehensive XSS tests
testXSSProtection();

// Test specific patterns
XSSTestPatterns.forEach(pattern => {
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

- Always escape user input when rendering HTML
- Use validation schemas for all user inputs
- Set up Content Security Policy headers
- Test your XSS protection regularly
- Escape output at the last possible moment before rendering

### ❌ DON'T

- Never trust user input
- Don't use `dangerouslySetInnerHTML` without escaping
- Don't strip/sanitize input unless absolutely necessary
- Don't rely only on client-side validation
- Don't concatenate user input directly into HTML strings

## Migration Guide

### Updating Existing Code

1. **Replace basic sanitization**:

   ```typescript
   // Old
   const clean = userInput.replace(/[<>]/g, '');
   
   // New
   const safe = escapeHtml(userInput);
   ```

2. **Update form validation**:

   ```typescript
   // Old
   const isValid = userInput.length > 0 && userInput.length < 100;
   
   // New
   const validated = safeUserInputSchema.parse(userInput);
   ```

3. **Secure URL handling**:

   ```typescript
   // Old
   const url = userInput.trim();
   
   // New
   const url = sanitizeUrl(userInput);
   if (!url) throw new Error('Invalid URL');
   ```

## Performance Notes

- Escaping functions are lightweight and performant
- Validation schemas cache compiled regexes
- Use validation schemas for forms, escaping for output
- Consider memoizing escaped content for frequently displayed data

## Development vs Production

The system includes development helpers:

```typescript
// Only logs in development
warnUnsafeContent(userInput, 'user comment');

// Test XSS protection in development
if (process.env.NODE_ENV === 'development') {
  testXSSProtection();
}
```

## Additional Resources

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [Content Security Policy Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [HTML Escaping Best Practices](https://www.owasp.org/index.php/XSS_(Cross_Site_Scripting)_Prevention_Cheat_Sheet)
