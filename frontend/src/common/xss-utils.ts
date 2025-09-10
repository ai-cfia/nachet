/**
 * XSS Protection Utilities and Usage Examples
 *
 * This file demonstrates how to properly use the XSS protection functions
 * from validation.ts to prevent Cross-Site Scripting attacks.
 */

import {
  escapeHtml,
  escapeHtmlAttribute,
  escapeJavaScript,
  sanitizeUrl,
  safeTextSchema,
  safeUserInputSchema,
  safeUrlSchema,
  generateCSP,
} from "./validation";

/**
 * Safe HTML rendering utility
 * Use this when you need to render user input in HTML
 */
export const renderSafeHtml = (userInput: string): string => {
  // Always escape user input before rendering
  return escapeHtml(userInput);
};

/**
 * Safe attribute rendering utility
 * Use this when setting HTML attributes with user input
 */
export const renderSafeAttribute = (userInput: string): string => {
  return escapeHtmlAttribute(userInput);
};

/**
 * Safe JavaScript string utility
 * Use this when embedding user input in JavaScript
 */
export const renderSafeJavaScript = (userInput: string): string => {
  return escapeJavaScript(userInput);
};

/**
 * Safe URL utility
 * Use this when rendering user-provided URLs
 */
export const renderSafeUrl = (userUrl: string): string | null => {
  return sanitizeUrl(userUrl);
};

/**
 * React-style safe rendering examples
 */
export const ReactExamples = {
  // ✅ Safe: User input is escaped
  SafeTextDisplay: (userText: string) => `
    <div className="user-content">
      ${escapeHtml(userText)}
    </div>
  `,

  // ✅ Safe: Attribute value is escaped
  SafeAttributeDisplay: (userTitle: string) => `
    <div title="${escapeHtmlAttribute(userTitle)}">
      Content
    </div>
  `,

  // ✅ Safe: URL is sanitized
  SafeLinkDisplay: (userUrl: string, linkText: string) => {
    const safeUrl = sanitizeUrl(userUrl);
    if (!safeUrl) return "<span>Invalid URL</span>";

    return `
      <a href="${escapeHtmlAttribute(safeUrl)}">
        ${escapeHtml(linkText)}
      </a>
    `;
  },

  // ❌ Dangerous: Never do this - direct insertion
  DangerousExample: (userInput: string) => `
    <div>${userInput}</div> <!-- XSS vulnerability! -->
  `,
};

/**
 * Form validation with XSS protection
 */
export const validateUserInput = {
  // Validate and sanitize text input
  text: (input: string) => {
    try {
      return safeTextSchema.parse(input);
    } catch (error) {
      console.error("Text validation error:", error);
      throw new Error("Invalid text input");
    }
  },

  // Validate and sanitize user input
  userInput: (input: string) => {
    try {
      return safeUserInputSchema.parse(input);
    } catch (error) {
      console.error("User input validation error:", error);
      throw new Error("Unsafe user input detected");
    }
  },

  // Validate and sanitize URL
  url: (input: string) => {
    try {
      return safeUrlSchema.parse(input);
    } catch (error) {
      console.error("URL validation error:", error);
      throw new Error("Invalid or unsafe URL");
    }
  },
};

/**
 * Template literal helper for safe HTML generation
 */
export const html = (strings: TemplateStringsArray, ...values: any[]) => {
  let result = "";
  for (let i = 0; i < strings.length; i++) {
    result += strings[i];
    if (i < values.length) {
      // Automatically escape all interpolated values
      const value = values[i];
      if (typeof value === "string") {
        result += escapeHtml(value);
      } else {
        result += String(value);
      }
    }
  }
  return result;
};

/**
 * Content Security Policy setup helper
 */
export const setupCSP = () => {
  const cspHeader = generateCSP();

  // For Express.js
  const expressMiddleware = (_req: any, res: any, next: any) => {
    res.setHeader("Content-Security-Policy", cspHeader);
    next();
  };

  // For meta tag (client-side)
  const metaTag = `<meta http-equiv="Content-Security-Policy" content="${cspHeader}">`;

  return {
    header: cspHeader,
    expressMiddleware,
    metaTag,
  };
};

/**
 * Common XSS attack patterns to test against
 * Use these for testing your XSS protection
 */
export const XSSTestPatterns = [
  '<script>alert("xss")</script>',
  '<img src="x" onerror="alert(\'xss\')">',
  'javascript:alert("xss")',
  'data:text/html,<script>alert("xss")</script>',
  "<svg onload=\"alert('xss')\">",
  "<iframe src=\"javascript:alert('xss')\"></iframe>",
  '"><script>alert("xss")</script>',
  "'><script>alert('xss')</script>",
  "<style>body{background:url(\"javascript:alert('xss')\")}</style>",
  '<link rel="stylesheet" href="javascript:alert(\'xss\')">',
];

/**
 * Test function to verify XSS protection
 */
export const testXSSProtection = () => {
  console.log("Testing XSS protection...");

  XSSTestPatterns.forEach((pattern, index) => {
    const escaped = escapeHtml(pattern);
    const safe = escaped !== pattern;
    console.log(`Test ${index + 1}: ${safe ? "✅ SAFE" : "❌ VULNERABLE"}`);
    console.log(`  Original: ${pattern}`);
    console.log(`  Escaped:  ${escaped}`);
    console.log("");
  });
};

/**
 * Development helper: Log unsafe content warnings
 */
export const warnUnsafeContent = (content: string, context: string) => {
  if (process.env.NODE_ENV === "development") {
    const hasScript = /<script|javascript:|data:|on\w+=/i.test(content);
    if (hasScript) {
      console.warn(
        `⚠️  Potentially unsafe content detected in ${context}:`,
        content,
      );
    }
  }
};
