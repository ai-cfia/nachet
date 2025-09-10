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
