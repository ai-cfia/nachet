import { describe, it, expect } from "vitest";
import {
  directoryNameSchema,
  emailSchema,
  passwordSchema,
  folderNameSchema,
  seedCountSchema,
  zoomLevelSchema,
  imageLabelSchema,
  classLabelSchema,
  imageFileSchema,
  fileListSchema,
  deviceIdSchema,
  imageFormatSchema,
  booleanSchema,
  sanitizeString,
  sanitizeEmail,
  sanitizeFileName,
  // XSS Protection functions
  escapeHtml,
  escapeHtmlAttribute,
  escapeJavaScript,
  sanitizeUrl,
  stripDangerousHtml,
  generateCSP,
  // XSS-Safe validation schemas
  safeTextSchema,
  safeHtmlSchema,
  safeUrlSchema,
  safeUserInputSchema,
  safeImageLabelSchema,
  safeClassLabelSchema,
  type DirectoryName,
  type Email,
  type Password,
  type FolderName,
  type SeedCount,
  type ZoomLevel,
  type ImageLabel,
  type ClassLabel,
  type DeviceId,
  type ImageFormat,
  // XSS-Safe types
} from "../validation";

describe("Validation Schemas", () => {
  describe("directoryNameSchema", () => {
    it("should validate valid directory names", () => {
      const validNames = [
        "test",
        "test123",
        "test_dir",
        "test-dir",
        "Test_Dir-123",
      ];

      validNames.forEach((name) => {
        const result = directoryNameSchema.safeParse(name);
        expect(result.success).toBe(true);
        expect(result.data).toBe(name.trim());
      });
    });

    it("should reject invalid directory names", () => {
      const invalidNames = [
        "",
        "_test", // starts with underscore
        "test_", // ends with underscore
        "-test", // starts with hyphen
        "test-", // ends with hyphen
        "test@dir", // invalid character
        "test dir", // space in middle
        "test.dir", // dot
      ];

      invalidNames.forEach((name) => {
        const result = directoryNameSchema.safeParse(name);
        expect(result.success).toBe(false);
      });
    });

    it("should trim whitespace", () => {
      const result = directoryNameSchema.safeParse("  test  ");
      expect(result.success).toBe(true);
      expect(result.data).toBe("test");
    });

    it("should reject names that are too long", () => {
      const longName = "a".repeat(256);
      const result = directoryNameSchema.safeParse(longName);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toContain("too long");
      }
    });
  });

  describe("emailSchema", () => {
    it("should validate valid email addresses", () => {
      const validEmails = [
        "test@example.com",
        "user.name@domain.co.uk",
        "test+tag@gmail.com",
        "user@subdomain.domain.com",
      ];

      validEmails.forEach((email) => {
        const result = emailSchema.safeParse(email);
        expect(result.success).toBe(true);
        expect(result.data).toBe(email.trim().toLowerCase());
      });
    });

    it("should reject invalid email addresses", () => {
      const invalidEmails = [
        "",
        "invalid",
        "@example.com",
        "test@",
        "test.example.com",
        "test@.com",
        "test..test@example.com",
      ];

      invalidEmails.forEach((email) => {
        const result = emailSchema.safeParse(email);
        expect(result.success).toBe(false);
      });
    });

    it("should sanitize and lowercase email", () => {
      const result = emailSchema.safeParse("  Test.User@Example.COM  ");
      expect(result.success).toBe(true);
      expect(result.data).toBe("test.user@example.com");
    });

    it("should reject emails that are too long", () => {
      const longEmail = "a".repeat(250) + "@example.com";
      const result = emailSchema.safeParse(longEmail);
      expect(result.success).toBe(false);
    });
  });

  describe("passwordSchema", () => {
    it("should validate strong passwords", () => {
      const validPasswords = [
        "Password123",
        "TestPass1",
        "MySecurePass2024",
        "Abc123Def",
      ];

      validPasswords.forEach((password) => {
        const result = passwordSchema.safeParse(password);
        expect(result.success).toBe(true);
        expect(result.data).toBe(password);
      });
    });

    it("should reject weak passwords", () => {
      const invalidPasswords = [
        "",
        "short",
        "nouppercase123",
        "NOLOWERCASE123",
        "NoNumbers",
        "Password", // no numbers
        "12345678", // no letters
      ];

      invalidPasswords.forEach((password) => {
        const result = passwordSchema.safeParse(password);
        expect(result.success).toBe(false);
      });
    });

    it("should reject passwords that are too short", () => {
      const result = passwordSchema.safeParse("Pass1");
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toContain(
          "at least 8 characters",
        );
      }
    });

    it("should reject passwords that are too long", () => {
      const longPassword = "A".repeat(129) + "1a";
      const result = passwordSchema.safeParse(longPassword);
      expect(result.success).toBe(false);
    });
  });

  describe("folderNameSchema", () => {
    it("should validate valid folder names", () => {
      const validNames = [
        "",
        "test",
        "test123",
        "test_dir",
        "test-dir",
        "Test_Dir-123",
      ];

      validNames.forEach((name) => {
        const result = folderNameSchema.safeParse(name);
        expect(result.success).toBe(true);
        expect(result.data).toBe(name.trim());
      });
    });

    it("should reject invalid folder names", () => {
      const invalidNames = [
        "test@dir", // invalid character
        "test.dir", // dot
        "test/dir", // slash
      ];

      invalidNames.forEach((name) => {
        const result = folderNameSchema.safeParse(name);
        expect(result.success).toBe(false);
      });
    });

    it("should allow empty folder names", () => {
      const result = folderNameSchema.safeParse("");
      expect(result.success).toBe(true);
      expect(result.data).toBe("");
    });
  });

  describe("seedCountSchema", () => {
    it("should validate valid seed counts", () => {
      const validCounts = [1, 10, 50, 100];

      validCounts.forEach((count) => {
        const result = seedCountSchema.safeParse(count);
        expect(result.success).toBe(true);
        expect(result.data).toBe(count);
      });
    });

    it("should reject invalid seed counts", () => {
      const invalidCounts = [0, -1, 1.5, 101, "10" as any];

      invalidCounts.forEach((count) => {
        const result = seedCountSchema.safeParse(count);
        expect(result.success).toBe(false);
      });
    });

    it("should reject non-integer values", () => {
      const result = seedCountSchema.safeParse(1.5);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toContain("whole number");
      }
    });
  });

  describe("zoomLevelSchema", () => {
    it("should validate valid zoom levels", () => {
      const validZooms = [0.1, 1, 10, 50, 100];

      validZooms.forEach((zoom) => {
        const result = zoomLevelSchema.safeParse(zoom);
        expect(result.success).toBe(true);
        expect(result.data).toBe(zoom);
      });
    });

    it("should reject invalid zoom levels", () => {
      const invalidZooms = [0, -1, 0.05, 100.1, 101];

      invalidZooms.forEach((zoom) => {
        const result = zoomLevelSchema.safeParse(zoom);
        expect(result.success).toBe(false);
      });
    });
  });

  describe("imageLabelSchema", () => {
    it("should validate valid image labels", () => {
      const validLabels = [
        "test",
        "Test Image",
        "image_123",
        "test-image",
        "Test.Image(1)",
        "test,image_label",
      ];

      validLabels.forEach((label) => {
        const result = imageLabelSchema.safeParse(label);
        expect(result.success).toBe(true);
        expect(result.data).toBe(label.trim());
      });
    });

    it("should reject invalid image labels", () => {
      const invalidLabels = [
        "",
        "test@image", // invalid character
        "test/image", // slash
        "test<image>", // angle brackets
      ];

      invalidLabels.forEach((label) => {
        const result = imageLabelSchema.safeParse(label);
        expect(result.success).toBe(false);
      });
    });

    it("should reject labels that are too long", () => {
      const longLabel = "a".repeat(101);
      const result = imageLabelSchema.safeParse(longLabel);
      expect(result.success).toBe(false);
    });
  });

  describe("classLabelSchema", () => {
    it("should validate valid class labels", () => {
      const validLabels = [
        "test",
        "Test Class",
        "class_123",
        "test-class",
        "Test_Class",
      ];

      validLabels.forEach((label) => {
        const result = classLabelSchema.safeParse(label);
        expect(result.success).toBe(true);
        expect(result.data).toBe(label.trim());
      });
    });

    it("should reject invalid class labels", () => {
      const invalidLabels = [
        "",
        "test@class", // invalid character
        "test.class", // dot
        "test/class", // slash
        "test,class", // comma
      ];

      invalidLabels.forEach((label) => {
        const result = classLabelSchema.safeParse(label);
        expect(result.success).toBe(false);
      });
    });
  });

  describe("imageFileSchema", () => {
    it("should validate valid image files", () => {
      const validFile = new File(["test"], "test.png", { type: "image/png" });
      const result = imageFileSchema.safeParse(validFile);
      expect(result.success).toBe(true);
      expect(result.data).toBe(validFile);
    });

    it("should reject files that are too large", () => {
      const largeFile = new File(
        [new ArrayBuffer(11 * 1024 * 1024)],
        "large.png",
        {
          type: "image/png",
        },
      );
      const result = imageFileSchema.safeParse(largeFile);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toContain("10MB");
      }
    });

    it("should reject invalid file types", () => {
      const invalidFile = new File(["test"], "test.txt", {
        type: "text/plain",
      });
      const result = imageFileSchema.safeParse(invalidFile);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toContain("valid image format");
      }
    });
  });

  describe("fileListSchema", () => {
    it("should validate valid file lists", () => {
      const files = [
        new File(["test1"], "test1.png", { type: "image/png" }),
        new File(["test2"], "test2.png", { type: "image/png" }),
      ];

      // Create a proper FileList mock
      const fileList = Object.create(FileList.prototype);
      Object.defineProperty(fileList, "length", { value: 2 });
      Object.defineProperty(fileList, "0", { value: files[0] });
      Object.defineProperty(fileList, "1", { value: files[1] });
      fileList.item = (index: number) => files[index] || null;

      const result = fileListSchema.safeParse(fileList);
      expect(result.success).toBe(true);
    });

    it("should reject empty file lists", () => {
      const emptyFileList = Object.create(FileList.prototype);
      Object.defineProperty(emptyFileList, "length", { value: 0 });
      emptyFileList.item = () => null;
      const result = fileListSchema.safeParse(emptyFileList);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toContain("At least one file");
      }
    });

    it("should reject file lists that are too large", () => {
      const files = Array.from(
        { length: 101 },
        (_, i) => new File([`test${i}`], `test${i}.png`, { type: "image/png" }),
      );
      const fileList = Object.create(FileList.prototype);
      Object.defineProperty(fileList, "length", { value: 101 });
      files.forEach((file, i) => {
        Object.defineProperty(fileList, i.toString(), { value: file });
      });
      fileList.item = (index: number) => files[index] || null;

      const result = fileListSchema.safeParse(fileList);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toContain("more than 100 files");
      }
    });

    it("should reject file lists with invalid files", () => {
      const files = [
        new File(["test1"], "test1.png", { type: "image/png" }),
        new File(["test2"], "test2.txt", { type: "text/plain" }),
      ];
      const fileList = Object.create(FileList.prototype);
      Object.defineProperty(fileList, "length", { value: 2 });
      Object.defineProperty(fileList, "0", { value: files[0] });
      Object.defineProperty(fileList, "1", { value: files[1] });
      fileList.item = (index: number) => files[index] || null;

      const result = fileListSchema.safeParse(fileList);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toContain("valid images");
      }
    });
  });

  describe("deviceIdSchema", () => {
    it("should validate valid device IDs", () => {
      const validIds = ["device1", "camera-123", "webcam_test"];

      validIds.forEach((id) => {
        const result = deviceIdSchema.safeParse(id);
        expect(result.success).toBe(true);
        expect(result.data).toBe(id);
      });
    });

    it("should reject invalid device IDs", () => {
      const invalidIds = ["", "a".repeat(101)];

      invalidIds.forEach((id) => {
        const result = deviceIdSchema.safeParse(id);
        expect(result.success).toBe(false);
      });
    });
  });

  describe("imageFormatSchema", () => {
    it("should validate valid image formats", () => {
      const result = imageFormatSchema.safeParse("image/png");
      expect(result.success).toBe(true);
      expect(result.data).toBe("image/png");
    });

    it("should reject invalid image formats", () => {
      const result = imageFormatSchema.safeParse("image/jpeg");
      expect(result.success).toBe(false);
    });
  });

  describe("booleanSchema", () => {
    it("should validate boolean values", () => {
      const result1 = booleanSchema.safeParse(true);
      const result2 = booleanSchema.safeParse(false);

      expect(result1.success).toBe(true);
      expect(result2.success).toBe(true);
      expect(result1.data).toBe(true);
      expect(result2.data).toBe(false);
    });

    it("should reject non-boolean values", () => {
      const result = booleanSchema.safeParse("true");
      expect(result.success).toBe(false);
    });
  });
});

describe("Sanitization Helpers", () => {
  describe("sanitizeString", () => {
    it("should remove angle brackets", () => {
      expect(sanitizeString("<script>alert('xss')</script>")).toBe(
        "scriptalert('xss')script",
      );
      expect(sanitizeString("test < test >")).toBe("test  test");
    });

    it("should trim whitespace", () => {
      expect(sanitizeString("  test  ")).toBe("test");
      expect(sanitizeString("\t\ntest\n\t")).toBe("test");
    });

    it("should handle empty strings", () => {
      expect(sanitizeString("")).toBe("");
      expect(sanitizeString("   ")).toBe("");
    });
  });

  describe("sanitizeEmail", () => {
    it("should trim and lowercase email", () => {
      expect(sanitizeEmail("  Test.User@Example.COM  ")).toBe(
        "test.user@example.com",
      );
      expect(sanitizeEmail("USER@DOMAIN.COM")).toBe("user@domain.com");
    });

    it("should handle empty strings", () => {
      expect(sanitizeEmail("")).toBe("");
    });
  });

  describe("sanitizeFileName", () => {
    it("should remove invalid characters from filenames", () => {
      expect(sanitizeFileName("test<file>.png")).toBe("testfile.png");
      expect(sanitizeFileName("test@image.jpg")).toBe("testimage.jpg");
      expect(sanitizeFileName("test image (1).png")).toBe("test image (1).png");
    });

    it("should preserve valid characters", () => {
      expect(sanitizeFileName("test_123-file.name.png")).toBe(
        "test_123-file.name.png",
      );
    });

    it("should trim whitespace", () => {
      expect(sanitizeFileName("  test.png  ")).toBe("test.png");
    });
  });
});

describe("Type Inference", () => {
  it("should correctly infer types from schemas", () => {
    // Test that TypeScript correctly infers the types
    const directoryName: DirectoryName = "test";
    const email: Email = "test@example.com";
    const password: Password = "Password123";
    const folderName: FolderName = "test";
    const seedCount: SeedCount = 10;
    const zoomLevel: ZoomLevel = 1.5;
    const imageLabel: ImageLabel = "test image";
    const classLabel: ClassLabel = "test class";
    const deviceId: DeviceId = "device1";
    const imageFormat: ImageFormat = "image/png";

    // These should not cause TypeScript errors
    expect(typeof directoryName).toBe("string");
    expect(typeof email).toBe("string");
    expect(typeof password).toBe("string");
    expect(typeof folderName).toBe("string");
    expect(typeof seedCount).toBe("number");
    expect(typeof zoomLevel).toBe("number");
    expect(typeof imageLabel).toBe("string");
    expect(typeof classLabel).toBe("string");
    expect(typeof deviceId).toBe("string");
    expect(typeof imageFormat).toBe("string");
  });
});

describe("Error Messages", () => {
  it("should provide clear error messages", () => {
    const result = directoryNameSchema.safeParse("");
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toBe(
        "Directory name cannot be empty",
      );
    }

    const emailResult = emailSchema.safeParse("invalid");
    expect(emailResult.success).toBe(false);
    if (!emailResult.success) {
      expect(emailResult.error.issues[0].message).toBe(
        "Please enter a valid email address",
      );
    }

    const passwordResult = passwordSchema.safeParse("weak");
    expect(passwordResult.success).toBe(false);
    if (!passwordResult.success) {
      expect(passwordResult.error.issues[0].message).toContain(
        "at least 8 characters",
      );
    }
  });
});

describe("Edge Cases", () => {
  it("should handle null and undefined values", () => {
    expect(directoryNameSchema.safeParse(null).success).toBe(false);
    expect(directoryNameSchema.safeParse(undefined).success).toBe(false);
    expect(emailSchema.safeParse(null).success).toBe(false);
    expect(passwordSchema.safeParse(undefined).success).toBe(false);
  });

  it("should handle numeric strings for numeric schemas", () => {
    expect(seedCountSchema.safeParse("10").success).toBe(false);
    expect(zoomLevelSchema.safeParse("1.5").success).toBe(false);
  });

  it("should handle special characters in strings", () => {
    expect(sanitizeString("test<script>alert('xss')</script>test")).toBe(
      "testscriptalert('xss')scripttest",
    );
    expect(sanitizeFileName("test<file>name.png")).toBe("testfilename.png");
  });

  it("should handle very long strings", () => {
    const longString = "a".repeat(1000);
    expect(directoryNameSchema.safeParse(longString).success).toBe(false);
    expect(folderNameSchema.safeParse(longString).success).toBe(false);
  });
});

describe("XSS Protection Functions", () => {
  describe("escapeHtml", () => {
    it("should escape HTML special characters", () => {
      expect(escapeHtml("<script>alert('xss')</script>")).toBe(
        "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;&#x2F;script&gt;",
      );
      expect(escapeHtml('Hello "World" & <test>')).toBe(
        "Hello &quot;World&quot; &amp; &lt;test&gt;",
      );
      expect(escapeHtml("Test `code` = value")).toBe(
        "Test &#x60;code&#x60; &#x3D; value",
      );
    });

    it("should handle empty and normal strings", () => {
      expect(escapeHtml("")).toBe("");
      expect(escapeHtml("normal text")).toBe("normal text");
      expect(escapeHtml("123456")).toBe("123456");
    });

    it("should escape all dangerous characters", () => {
      const dangerous = "&<>\"'`=/";
      const expected = "&amp;&lt;&gt;&quot;&#x27;&#x60;&#x3D;&#x2F;";
      expect(escapeHtml(dangerous)).toBe(expected);
    });
  });

  describe("escapeHtmlAttribute", () => {
    it("should escape HTML attribute characters", () => {
      expect(escapeHtmlAttribute('value="test"')).toBe(
        "value=&quot;test&quot;",
      );
      expect(escapeHtmlAttribute("value='test'")).toBe(
        "value=&#x27;test&#x27;",
      );
      expect(escapeHtmlAttribute("onclick=alert('xss')")).toBe(
        "onclick=alert(&#x27;xss&#x27;)",
      );
    });

    it("should handle ampersands and angle brackets", () => {
      expect(escapeHtmlAttribute("value & <test>")).toBe(
        "value &amp; &lt;test&gt;",
      );
    });
  });

  describe("escapeJavaScript", () => {
    it("should escape JavaScript special characters", () => {
      expect(escapeJavaScript('alert("Hello")')).toBe('alert(\\"Hello\\")');
      expect(escapeJavaScript("line1\nline2")).toBe("line1\\nline2");
      expect(escapeJavaScript("tab\there")).toBe("tab\\there");
    });

    it("should escape dangerous Unicode characters", () => {
      expect(escapeJavaScript("<script>")).toBe("\\u003Cscript\\u003E");
      expect(escapeJavaScript("</script>")).toBe("\\u003C/script\\u003E");
      expect(escapeJavaScript("a & b = c")).toBe("a \\u0026 b \\u003D c");
    });

    it("should handle control characters", () => {
      expect(escapeJavaScript("test\r\n")).toBe("test\\r\\n");
      expect(escapeJavaScript("test\t\b\f")).toBe("test\\t\\b\\f");
      expect(escapeJavaScript("test\v\0")).toBe("test\\v\\0");
    });
  });

  describe("sanitizeUrl", () => {
    it("should allow safe URLs", () => {
      expect(sanitizeUrl("https://example.com")).toBe("https://example.com");
      expect(sanitizeUrl("http://test.org")).toBe("http://test.org");
      expect(sanitizeUrl("ftp://files.com")).toBe("ftp://files.com");
      expect(sanitizeUrl("mailto:test@example.com")).toBe(
        "mailto:test@example.com",
      );
    });

    it("should allow relative URLs", () => {
      expect(sanitizeUrl("/path/to/page")).toBe("/path/to/page");
      expect(sanitizeUrl("./relative/path")).toBe("./relative/path");
      expect(sanitizeUrl("../parent/path")).toBe("../parent/path");
      expect(sanitizeUrl("path/without/slash")).toBe("path/without/slash");
    });

    it("should block dangerous URLs", () => {
      expect(sanitizeUrl("javascript:alert('xss')")).toBe(null);
      expect(sanitizeUrl("data:text/html,<script>alert('xss')</script>")).toBe(
        null,
      );
      expect(sanitizeUrl("vbscript:alert('xss')")).toBe(null);
      expect(sanitizeUrl("file:///etc/passwd")).toBe(null);
      expect(sanitizeUrl("about:blank")).toBe(null);
    });

    it("should block unsafe protocols case-insensitively", () => {
      expect(sanitizeUrl("JAVASCRIPT:alert('xss')")).toBe(null);
      expect(sanitizeUrl("Data:text/html,<script>")).toBe(null);
      expect(sanitizeUrl("VBScript:alert('xss')")).toBe(null);
    });

    it("should handle whitespace", () => {
      expect(sanitizeUrl("  https://example.com  ")).toBe(
        "https://example.com",
      );
      expect(sanitizeUrl("\t\njavascript:alert('xss')\r\n")).toBe(null);
    });
  });

  describe("stripDangerousHtml", () => {
    it("should remove script tags", () => {
      expect(stripDangerousHtml("<script>alert('xss')</script>")).toBe("");
      expect(
        stripDangerousHtml("Hello <script src='evil.js'></script> World"),
      ).toBe("Hello  World");
    });

    it("should remove dangerous tags", () => {
      expect(stripDangerousHtml("<iframe src='evil.com'></iframe>")).toBe("");
      expect(stripDangerousHtml("<object data='evil.swf'></object>")).toBe("");
      expect(stripDangerousHtml("<embed src='evil.swf'>")).toBe("");
      expect(
        stripDangerousHtml("<link rel='stylesheet' href='evil.css'>"),
      ).toBe("");
      expect(
        stripDangerousHtml(
          "<meta http-equiv='refresh' content='0;url=evil.com'>",
        ),
      ).toBe("");
      expect(
        stripDangerousHtml(
          "<style>body{background:url(javascript:alert('xss'))}</style>",
        ),
      ).toBe("");
    });

    it("should remove event handlers", () => {
      const result1 = stripDangerousHtml(
        "<div onclick=\"alert('xss')\">Click</div>",
      );
      expect(result1).not.toContain('onclick="alert(');
      expect(result1).toContain("Click");

      const result2 = stripDangerousHtml(
        '<img onload="alert(\'xss\')" src="test.jpg">',
      );
      expect(result2).not.toContain('onload="alert(');
      expect(result2).toContain('src="test.jpg">');

      const result3 = stripDangerousHtml(
        "<button onmouseover=\"alert('xss')\">Hover</button>",
      );
      expect(result3).not.toContain('onmouseover="alert(');
      expect(result3).toContain("Hover");
    });

    it("should remove javascript: and data: URLs", () => {
      const result1 = stripDangerousHtml(
        "<a href=\"javascript:alert('xss')\">Link</a>",
      );
      expect(result1).not.toContain("javascript:alert(");
      expect(result1).toContain("Link");

      const result2 = stripDangerousHtml(
        "<img src=\"data:text/html,<script>alert('xss')</script>\">",
      );
      expect(result2).not.toContain("data:text/html");
      expect(result2).not.toContain("<script>");
    });

    it("should preserve safe HTML", () => {
      const safeHtml =
        "<p>Hello <strong>World</strong></p><ul><li>Item 1</li></ul>";
      expect(stripDangerousHtml(safeHtml)).toBe(safeHtml);
    });
  });

  describe("generateCSP", () => {
    it("should generate valid CSP header", () => {
      const csp = generateCSP();
      expect(csp).toContain("default-src 'self'");
      expect(csp).toContain("script-src 'self' 'unsafe-inline'");
      expect(csp).toContain("object-src 'none'");
      expect(csp).toContain("upgrade-insecure-requests");
    });

    it("should format directives correctly", () => {
      const csp = generateCSP();
      // Should use kebab-case for directive names
      expect(csp).toContain("default-src");
      expect(csp).toContain("script-src");
      expect(csp).toContain("style-src");
      expect(csp).toContain("img-src");
      expect(csp).toContain("frame-ancestors");
      // Should separate directives with semicolons
      expect(csp.split(";").length).toBeGreaterThan(5);
    });
  });
});

describe("XSS-Safe Validation Schemas", () => {
  describe("safeTextSchema", () => {
    it("should validate safe text input", () => {
      const validTexts = [
        "Hello World",
        "This is a normal text",
        "Text with numbers 123 and symbols !@#",
        "Multi word text input",
      ];

      validTexts.forEach((text) => {
        const result = safeTextSchema.safeParse(text);
        expect(result.success).toBe(true);
        expect(result.data).toBe(text.trim());
      });
    });

    it("should reject empty or too long text", () => {
      expect(safeTextSchema.safeParse("").success).toBe(false);
      expect(safeTextSchema.safeParse("   ").success).toBe(false);
      expect(safeTextSchema.safeParse("a".repeat(1001)).success).toBe(false);
    });

    it("should trim whitespace", () => {
      const result = safeTextSchema.safeParse("  Hello World  ");
      expect(result.success).toBe(true);
      expect(result.data).toBe("Hello World");
    });
  });

  describe("safeUserInputSchema", () => {
    it("should validate safe user input", () => {
      const validInputs = [
        "John Doe",
        "This is my comment",
        "Email: user@example.com",
        "Phone: +1-234-567-8900",
      ];

      validInputs.forEach((input) => {
        const result = safeUserInputSchema.safeParse(input);
        expect(result.success).toBe(true);
        expect(result.data).toBe(input.trim());
      });
    });

    it("should reject dangerous input patterns", () => {
      const dangerousInputs = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        "vbscript:alert('xss')",
        "Hello <script>alert('xss')</script> World",
      ];

      dangerousInputs.forEach((input) => {
        const result = safeUserInputSchema.safeParse(input);
        expect(result.success).toBe(false);
      });
    });

    it("should handle length limits", () => {
      expect(safeUserInputSchema.safeParse("").success).toBe(false);
      expect(safeUserInputSchema.safeParse("a".repeat(501)).success).toBe(
        false,
      );
      expect(safeUserInputSchema.safeParse("a".repeat(500)).success).toBe(true);
    });
  });

  describe("safeUrlSchema", () => {
    it("should validate safe URLs", () => {
      const validUrls = [
        "https://example.com",
        "http://test.org/path",
        "/relative/path",
        "./file.html",
        "mailto:test@example.com",
      ];

      validUrls.forEach((url) => {
        const result = safeUrlSchema.safeParse(url);
        expect(result.success).toBe(true);
        expect(result.data).toBe(url.trim());
      });
    });

    it("should reject dangerous URLs", () => {
      const dangerousUrls = [
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        "vbscript:alert('xss')",
        "file:///etc/passwd",
      ];

      dangerousUrls.forEach((url) => {
        const result = safeUrlSchema.safeParse(url);
        expect(result.success).toBe(false);
      });
    });

    it("should handle URL length limits", () => {
      expect(safeUrlSchema.safeParse("").success).toBe(false);
      expect(safeUrlSchema.safeParse("a".repeat(2049)).success).toBe(false);

      // Test a URL that's within the limit and valid
      const validUrl = "https://example.com";
      expect(safeUrlSchema.safeParse(validUrl).success).toBe(true);

      // Test a URL that exceeds the 2048 character limit
      const tooLongUrl = "https://" + "a".repeat(2050) + ".com";
      expect(safeUrlSchema.safeParse(tooLongUrl).success).toBe(false);
    });
  });

  describe("safeImageLabelSchema", () => {
    it("should validate safe image labels", () => {
      const validLabels = [
        "My Image",
        "Test_Image-123",
        "Image (version 2.0)",
        "file.name",
        "Dataset, Part 1",
      ];

      validLabels.forEach((label) => {
        const result = safeImageLabelSchema.safeParse(label);
        expect(result.success).toBe(true);
        expect(result.data).toBe(label.trim());
      });
    });

    it("should reject labels with dangerous characters", () => {
      const dangerousLabels = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "data:text/html,<script>",
        "Image <test>",
        "Label > test",
        "Label &lt;script&gt;",
      ];

      dangerousLabels.forEach((label) => {
        const result = safeImageLabelSchema.safeParse(label);
        expect(result.success).toBe(false);
      });
    });

    it("should reject invalid characters", () => {
      const invalidLabels = [
        "label@email.com",
        "label#hashtag",
        "label$money",
        "label%percent",
        "label&amp;",
        "label*star",
        "label+plus",
        "label[bracket]",
        "label{brace}",
        "label|pipe",
        "label\\backslash",
        "label:colon",
        "label;semicolon",
        "label<less>",
        "label=equals",
        "label?question",
        "label^caret",
        "label~tilde",
        "label`backtick",
      ];

      invalidLabels.forEach((label) => {
        const result = safeImageLabelSchema.safeParse(label);
        expect(result.success).toBe(false);
      });
    });
  });

  describe("safeClassLabelSchema", () => {
    it("should validate safe class labels", () => {
      const validLabels = [
        "ClassName",
        "Class_Name",
        "Class-Name",
        "Class Name 123",
        "Dataset_v2",
      ];

      validLabels.forEach((label) => {
        const result = safeClassLabelSchema.safeParse(label);
        expect(result.success).toBe(true);
        expect(result.data).toBe(label.trim());
      });
    });

    it("should reject labels with dangerous patterns", () => {
      const dangerousLabels = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "data:text/html,<script>",
        "Class <test>",
        "Class &lt;script&gt;",
      ];

      dangerousLabels.forEach((label) => {
        const result = safeClassLabelSchema.safeParse(label);
        expect(result.success).toBe(false);
      });
    });

    it("should reject invalid characters", () => {
      const invalidLabels = [
        "class.name",
        "class,name",
        "class(name)",
        "class@name",
        "class#name",
        "class$name",
        "class%name",
        "class&name",
        "class*name",
      ];

      invalidLabels.forEach((label) => {
        const result = safeClassLabelSchema.safeParse(label);
        expect(result.success).toBe(false);
      });
    });
  });

  describe("safeHtmlSchema", () => {
    it("should strip dangerous HTML while preserving safe content", () => {
      const input =
        '<p>Hello</p><script>alert("xss")</script><strong>World</strong>';
      const result = safeHtmlSchema.safeParse(input);
      expect(result.success).toBe(true);
      expect(result.data).toBe("<p>Hello</p><strong>World</strong>");
    });

    it("should handle content length limits", () => {
      expect(safeHtmlSchema.safeParse("a".repeat(10001)).success).toBe(false);
      expect(safeHtmlSchema.safeParse("a".repeat(10000)).success).toBe(true);
    });

    it("should remove all dangerous elements", () => {
      const dangerousHtml = `
        <script>alert('xss')</script>
        <iframe src="evil.com"></iframe>
        <object data="evil.swf"></object>
        <embed src="evil.swf">
        <link rel="stylesheet" href="evil.css">
        <style>body{background:url(javascript:alert('xss'))}</style>
        <div onclick="alert('xss')">Click me</div>
        <p>Safe content</p>
      `;

      const result = safeHtmlSchema.safeParse(dangerousHtml);
      expect(result.success).toBe(true);
      expect(result.data).toContain("<p>Safe content</p>");
      expect(result.data).not.toContain("<script>");
      expect(result.data).not.toContain("<iframe>");
      expect(result.data).not.toContain("onclick");
      expect(result.data).not.toContain("javascript:");
    });
  });
});

describe("XSS Attack Vector Tests", () => {
  const xssPayloads = [
    '<script>alert("XSS")</script>',
    '<img src="x" onerror="alert(\'XSS\')">',
    "<svg onload=\"alert('XSS')\">",
    "<iframe src=\"javascript:alert('XSS')\"></iframe>",
    "<object data=\"javascript:alert('XSS')\"></object>",
    "<embed src=\"javascript:alert('XSS')\">",
    '<link rel="stylesheet" href="javascript:alert(\'XSS\')">',
    "<style>body{background:url(\"javascript:alert('XSS')\")}</style>",
    '"><script>alert("XSS")</script>',
    "'><script>alert('XSS')</script>",
    "<div onclick=\"alert('XSS')\">Click me</div>",
    "<a href=\"javascript:alert('XSS')\">Click me</a>",
    "<form action=\"javascript:alert('XSS')\">",
    '<meta http-equiv="refresh" content="0;url=javascript:alert(\'XSS\')">',
    'javascript:alert("XSS")',
    'data:text/html,<script>alert("XSS")</script>',
    'vbscript:alert("XSS")',
  ];

  describe("escapeHtml protection", () => {
    it("should neutralize all XSS payloads", () => {
      xssPayloads.forEach((payload) => {
        const escaped = escapeHtml(payload);
        expect(escaped).not.toContain("<script");
        // Note: javascript: will be escaped but still visible as text - this is expected
        expect(escaped).not.toContain("onerror=");
        expect(escaped).not.toContain("onload=");
        expect(escaped).not.toContain("onclick=");
        // Should contain escaped versions
        if (payload.includes("<")) {
          expect(escaped).toContain("&lt;");
        }
        if (payload.includes(">")) {
          expect(escaped).toContain("&gt;");
        }
      });
    });
  });

  describe("sanitizeUrl protection", () => {
    it("should block dangerous URL payloads", () => {
      const urlPayloads = [
        'javascript:alert("XSS")',
        'data:text/html,<script>alert("XSS")</script>',
        'vbscript:alert("XSS")',
        "file:///etc/passwd",
        "about:blank",
      ];

      urlPayloads.forEach((payload) => {
        const result = sanitizeUrl(payload);
        expect(result).toBe(null);
      });
    });
  });

  describe("stripDangerousHtml protection", () => {
    it("should remove dangerous elements from XSS payloads", () => {
      xssPayloads.forEach((payload) => {
        const cleaned = stripDangerousHtml(payload);
        expect(cleaned).not.toContain("<script");
        expect(cleaned).not.toContain("<iframe");
        expect(cleaned).not.toContain("<object");
        expect(cleaned).not.toContain("<embed");
        expect(cleaned).not.toContain("<link");
        expect(cleaned).not.toContain("<style");
        expect(cleaned).not.toContain("javascript:");
        expect(cleaned).not.toContain("data:");
        expect(cleaned).not.toContain("onclick=");
        expect(cleaned).not.toContain("onerror=");
        expect(cleaned).not.toContain("onload=");
      });
    });
  });

  describe("safeUserInputSchema protection", () => {
    it("should reject dangerous input patterns", () => {
      const dangerousPatterns = [
        '<script>alert("XSS")</script>',
        'javascript:alert("XSS")',
        'data:text/html,<script>alert("XSS")</script>',
        'vbscript:alert("XSS")',
      ];

      dangerousPatterns.forEach((pattern) => {
        const result = safeUserInputSchema.safeParse(pattern);
        expect(result.success).toBe(false);
      });
    });
  });
});
