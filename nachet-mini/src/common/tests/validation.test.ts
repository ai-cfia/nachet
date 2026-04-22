import { describe, it, expect } from "vitest";
import {
  normalizeFileName,
  validateImageName,
  validateDescription,
} from "../validation";

describe("normalizeFileName", () => {
  it("replaces spaces with dashes", () => {
    expect(normalizeFileName("my photo.jpg")).toBe("my-photo.jpg");
  });

  it("collapses consecutive dashes", () => {
    expect(normalizeFileName("my---file.png")).toBe("my-file.png");
  });

  it("trims leading and trailing dashes", () => {
    expect(normalizeFileName("-file-.txt")).toBe("file.txt");
  });

  it("lowercases the extension", () => {
    expect(normalizeFileName("FILE.PNG")).toBe("FILE.png");
  });

  it("preserves accented characters in the base name", () => {
    expect(normalizeFileName("café.jpg")).toBe("café.jpg");
  });

  it("falls back to 'image' when all base characters are invalid", () => {
    expect(normalizeFileName("!!!.jpg")).toBe("image.jpg");
  });

  it("handles filename with no extension", () => {
    expect(normalizeFileName("myfile")).toBe("myfile");
  });

  it("returns just 'image' when base is empty and no extension", () => {
    expect(normalizeFileName("!!!")).toBe("image");
  });

  it("truncates base to fit within 100 characters total", () => {
    const longBase = "a".repeat(300);
    const result = normalizeFileName(longBase + ".png");
    const base = result.replace(".png", "");
    expect(base.length).toBe(96);
  });

  it("replaces special chars (exclamation, hash) with dashes then collapses", () => {
    expect(normalizeFileName("a!b#c.jpg")).toBe("a-b-c.jpg");
  });

  it("handles filenames with multiple dots (e.g. archive.tar.gz)", () => {
    expect(normalizeFileName("archive.tar.gz")).toBe("archive.tar.gz");
  });

  it("falls back to 'image' when trimming leaves an empty string", () => {
    expect(normalizeFileName("---.jpg")).toBe("image.jpg");
  });
});

describe("validateImageName", () => {
  it("returns null for a valid alphanumeric name", () => {
    expect(validateImageName("photo123")).toBeNull();
  });

  it("returns null for a name with dots and hyphens", () => {
    expect(validateImageName("my-photo.jpg")).toBeNull();
  });

  it("returns null for a name of exactly 100 characters", () => {
    expect(validateImageName("a".repeat(100))).toBeNull();
  });

  it("returns imageNameRequired for empty string", () => {
    expect(validateImageName("")).toBe("metadata.validation.imageNameRequired");
  });

  it("returns imageNameTooLong for 101-character name", () => {
    expect(validateImageName("a".repeat(101))).toBe(
      "metadata.validation.imageNameTooLong",
    );
  });

  it("returns imageNameInvalid for a name containing a space", () => {
    expect(validateImageName("my photo")).toBe(
      "metadata.validation.imageNameInvalid",
    );
  });

  it("returns null for a name containing an underscore", () => {
    expect(validateImageName("my_photo")).toBeNull();
  });

  it("returns imageNameInvalid for a name containing special symbols", () => {
    expect(validateImageName("photo!")).toBe(
      "metadata.validation.imageNameInvalid",
    );
  });

  it("returns null for a 1-character valid name", () => {
    expect(validateImageName("a")).toBeNull();
  });

  it("returns null for an uppercase valid name", () => {
    expect(validateImageName("MY-PHOTO.JPG")).toBeNull();
  });

  it("returns null for a name with accented characters", () => {
    expect(validateImageName("café.jpg")).toBeNull();
  });
});

describe("validateDescription", () => {
  it("returns null for an empty string (empty is allowed)", () => {
    expect(validateDescription("")).toBeNull();
  });

  it("returns null for a valid description with letters, digits, spaces, and dots", () => {
    expect(validateDescription("Good image 123.")).toBeNull();
  });

  it("returns null for a description of exactly 1000 characters", () => {
    expect(validateDescription("a".repeat(1000))).toBeNull();
  });

  it("returns descriptionTooLong for a description of 1001 characters", () => {
    expect(validateDescription("a".repeat(1001))).toBe(
      "metadata.validation.descriptionTooLong",
    );
  });

  it("returns null for a description with an underscore", () => {
    expect(validateDescription("bad_underscore")).toBeNull();
  });

  it("returns null for a description with a comma", () => {
    expect(validateDescription("hello, world")).toBeNull();
  });

  it("returns null for a description with a newline", () => {
    expect(validateDescription("Line 1\nLine 2")).toBeNull();
  });
});
