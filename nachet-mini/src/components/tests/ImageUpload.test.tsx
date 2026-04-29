import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import frMain from "../../locales/fr/main";
import ImageUpload from "../ImageUpload";

const { mockValidateImageFile } = vi.hoisted(() => ({
  mockValidateImageFile: vi.fn(),
}));
vi.mock("@common/imageutils", () => ({
  validateImageFile: mockValidateImageFile,
}));

const makeFile = (name: string, type = "image/png") =>
  new File(["x"], name, { type });

const getFileInput = () =>
  document.querySelector("input[type=file]") as HTMLInputElement;

describe("ImageUpload", () => {
  const onClose = vi.fn();
  const onImageLoaded = vi.fn();

  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
    onClose.mockClear();
    onImageLoaded.mockClear();
    mockValidateImageFile.mockResolvedValue({
      isValid: true,
      errorKeys: [],
      dimensions: { width: 800, height: 600 },
    });
  });

  afterEach(cleanup);

  const renderUpload = (open = true) =>
    render(
      <I18nextProvider i18n={i18n}>
        <ImageUpload
          open={open}
          onClose={onClose}
          onImageLoaded={onImageLoaded}
        />
      </I18nextProvider>,
    );

  describe("when closed", () => {
    it("does not render the dialog when open is false", async () => {
      renderUpload(false);
      expect(await page.getByRole("dialog").all()).toHaveLength(0);
    });
  });

  describe("when open", () => {
    it("renders the dialog title", async () => {
      renderUpload();
      await expect
        .element(page.getByText(enMain.imageUpload.title))
        .toBeVisible();
    });

    it('renders the "Choose File(s)" button', async () => {
      renderUpload();
      await expect
        .element(
          page.getByRole("button", { name: enMain.imageUpload.chooseFile }),
        )
        .toBeVisible();
    });

    it("renders a close button", async () => {
      renderUpload();
      await expect
        .element(page.getByRole("button", { name: "close" }))
        .toBeVisible();
    });

    it("shows no error message by default", async () => {
      renderUpload();
      expect(
        await page.getByText(enMain.validation.invalidType).all(),
      ).toHaveLength(0);
    });

    it("accepts only PNG and JPEG files", async () => {
      renderUpload();
      expect(getFileInput().accept).toBe("image/png,image/jpeg");
    });

    it("allows selecting multiple files at once", async () => {
      renderUpload();
      expect(getFileInput().multiple).toBe(true);
    });
  });

  describe("close button", () => {
    it("calls onClose when clicked", async () => {
      renderUpload();
      await page.getByRole("button", { name: "close" }).click();
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("clicking the visible upload button triggers the hidden file input", async () => {
      renderUpload();
      const input = getFileInput();
      const clickSpy = vi.spyOn(input, "click");
      await page
        .getByRole("button", { name: enMain.imageUpload.chooseFile })
        .click();
      expect(clickSpy).toHaveBeenCalledOnce();
    });
  });

  describe("valid file upload", () => {
    it("calls onImageLoaded with data URL, dimensions, and filename", async () => {
      renderUpload();
      await userEvent.setup().upload(getFileInput(), makeFile("photo.png"));
      await vi.waitFor(() =>
        expect(onImageLoaded).toHaveBeenCalledWith(
          expect.stringMatching(/^data:image\/png;base64,/),
          [800, 600],
          "photo.png",
        ),
      );
    });

    it("calls onClose after a valid file is loaded", async () => {
      renderUpload();
      await userEvent.setup().upload(getFileInput(), makeFile("photo.png"));
      await vi.waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    });

    it("uses [0, 0] dimensions when validation succeeds without image dimensions", async () => {
      mockValidateImageFile.mockResolvedValue({
        isValid: true,
        errorKeys: [],
      });
      renderUpload();
      await userEvent.setup().upload(getFileInput(), makeFile("photo.png"));
      await vi.waitFor(() =>
        expect(onImageLoaded).toHaveBeenCalledWith(
          expect.stringMatching(/^data:image\/png;base64,/),
          [0, 0],
          "photo.png",
        ),
      );
    });

    it("calls onImageLoaded for each file when uploading multiple valid files", async () => {
      renderUpload();
      await userEvent
        .setup()
        .upload(getFileInput(), [makeFile("a.png"), makeFile("b.png")]);
      await vi.waitFor(() => expect(onImageLoaded).toHaveBeenCalledTimes(2));
    });

    it("calls onClose once after all valid files are processed", async () => {
      renderUpload();
      await userEvent
        .setup()
        .upload(getFileInput(), [makeFile("a.png"), makeFile("b.png")]);
      await vi.waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    });
  });

  describe("invalid file upload", () => {
    it("shows an error message containing the filename and validation error", async () => {
      mockValidateImageFile.mockResolvedValue({
        isValid: false,
        errorKeys: ["invalidType"],
      });
      renderUpload();
      await userEvent.setup().upload(getFileInput(), makeFile("doc.png"));
      await expect.element(page.getByText(/doc\.png/)).toBeVisible();
      await expect
        .element(page.getByText(enMain.validation.invalidType))
        .toBeVisible();
    });

    it("does not call onImageLoaded when validation fails", async () => {
      mockValidateImageFile.mockResolvedValue({
        isValid: false,
        errorKeys: ["invalidType"],
      });
      renderUpload();
      await userEvent.setup().upload(getFileInput(), makeFile("doc.png"));
      await expect.element(page.getByText(/doc\.png/)).toBeVisible();
      expect(onImageLoaded).not.toHaveBeenCalled();
    });

    it("does not call onClose when validation fails", async () => {
      mockValidateImageFile.mockResolvedValue({
        isValid: false,
        errorKeys: ["fileTooLarge"],
      });
      renderUpload();
      await userEvent.setup().upload(getFileInput(), makeFile("big.png"));
      await expect.element(page.getByText(/big\.png/)).toBeVisible();
      expect(onClose).not.toHaveBeenCalled();
    });

    it("shows errors for invalid files and still calls onImageLoaded for valid ones", async () => {
      mockValidateImageFile
        .mockResolvedValueOnce({
          isValid: true,
          errorKeys: [],
          dimensions: { width: 800, height: 600 },
        })
        .mockResolvedValueOnce({
          isValid: false,
          errorKeys: ["fileTooLarge"],
        });
      renderUpload();
      await userEvent
        .setup()
        .upload(getFileInput(), [makeFile("good.png"), makeFile("bad.png")]);
      await expect.element(page.getByText(/bad\.png/)).toBeVisible();
      expect(onImageLoaded).toHaveBeenCalledTimes(1);
      expect(onClose).not.toHaveBeenCalled();
    });

    it("clears the error when the dialog is closed and reopened", async () => {
      const view = renderUpload();
      mockValidateImageFile.mockResolvedValue({
        isValid: false,
        errorKeys: ["invalidType"],
      });
      await userEvent.setup().upload(getFileInput(), makeFile("doc.png"));
      await expect.element(page.getByText(/doc\.png/)).toBeVisible();

      await page.getByRole("button", { name: "close" }).click();
      expect(await page.getByText(/doc\.png/).all()).toHaveLength(0);

      view.rerender(
        <I18nextProvider i18n={i18n}>
          <ImageUpload
            open={false}
            onClose={onClose}
            onImageLoaded={onImageLoaded}
          />
        </I18nextProvider>,
      );
      view.rerender(
        <I18nextProvider i18n={i18n}>
          <ImageUpload open onClose={onClose} onImageLoaded={onImageLoaded} />
        </I18nextProvider>,
      );

      expect(await page.getByText(/doc\.png/).all()).toHaveLength(0);
    });
  });

  describe("i18n", () => {
    it("shows the French dialog title in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderUpload();
      await expect
        .element(page.getByText(frMain.imageUpload.title))
        .toBeVisible();
    });

    it("shows the French choose-file button label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderUpload();
      await expect
        .element(
          page.getByRole("button", { name: frMain.imageUpload.chooseFile }),
        )
        .toBeVisible();
    });
  });
});
