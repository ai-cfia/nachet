import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import frMain from "../../locales/fr/main";
import enCommon from "../../locales/en/common";
import frCommon from "../../locales/fr/common";
import { useImageStore } from "@stores/useImageStore";
import SaveDialog from "../SaveDialog";

const { mockSaveAs } = vi.hoisted(() => ({ mockSaveAs: vi.fn() }));
vi.mock("file-saver", () => ({ saveAs: mockSaveAs }));

const zipMock = vi.hoisted(() => ({
  file: vi.fn(),
  generateAsync: vi.fn(),
}));
vi.mock("jszip", async () => ({
  __esModule: true,
  default: function MockJSZip() {
    return zipMock;
  },
}));

vi.mock("@stores/useImageStore", () => ({ useImageStore: vi.fn() }));

const makeImage = (index: number, src = "data:image/png;base64,abc") => ({
  index,
  src,
  imageDims: [800, 600],
  metadata: { imageName: `image-${index}.png` },
  sha256: "",
});

const setStore = (
  images: ReturnType<typeof makeImage>[],
  currentImage?: ReturnType<typeof makeImage>,
) => {
  vi.mocked(useImageStore).mockImplementation((selector: any) =>
    selector({
      images,
      getCurrentImage: vi.fn().mockReturnValue(currentImage ?? images[0]),
    }),
  );
};

const setStoreWithoutCurrentImage = (
  images: ReturnType<typeof makeImage>[],
) => {
  vi.mocked(useImageStore).mockImplementation((selector: any) =>
    selector({
      images,
      getCurrentImage: vi.fn().mockReturnValue(undefined),
    }),
  );
};

describe("SaveDialog", () => {
  const onClose = vi.fn();

  const renderDialog = (open = true) =>
    render(
      <I18nextProvider i18n={i18n}>
        <SaveDialog open={open} onClose={onClose} />
      </I18nextProvider>,
    );

  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
    onClose.mockClear();
    mockSaveAs.mockClear();
    zipMock.file.mockClear();
    zipMock.generateAsync.mockReset();
    zipMock.generateAsync.mockResolvedValue(new Blob(["zip"]));
    setStore([]);
  });

  afterEach(cleanup);

  describe("when closed", () => {
    it("does not render the dialog when open is false", async () => {
      renderDialog(false);
      expect(await page.getByRole("dialog").all()).toHaveLength(0);
    });
  });

  describe("when open", () => {
    it("renders the dialog title", async () => {
      renderDialog();
      await expect
        .element(page.getByText(enMain.saveDialog.title))
        .toBeVisible();
    });

    it("renders a close button", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: "close" }))
        .toBeVisible();
    });

    it("renders the Current Image toggle button selected by default", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("button", { name: enMain.saveDialog.currentImage }),
        )
        .toHaveAttribute("aria-pressed", "true");
      await expect
        .element(
          page.getByRole("button", { name: enMain.saveDialog.allImages }),
        )
        .toHaveAttribute("aria-pressed", "false");
    });

    it("renders the All Images toggle button", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("button", { name: enMain.saveDialog.allImages }),
        )
        .toBeVisible();
    });

    it("shows the image name text field in individual mode by default", async () => {
      renderDialog();
      await expect.element(page.getByRole("textbox")).toBeVisible();
    });

    it("renders the Cancel button", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: enCommon.actions.cancel }))
        .toBeVisible();
    });

    it("renders the Save button", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: enCommon.actions.save }))
        .toBeVisible();
    });

    it("disables the Save button when there are no images", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: enCommon.actions.save }))
        .toBeDisabled();
    });

    it("enables the Save button when images are present", async () => {
      setStore([makeImage(0)]);
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: enCommon.actions.save }))
        .not.toBeDisabled();
    });
  });

  describe("mode toggle", () => {
    it("hides the image name field when switching to All Images mode", async () => {
      renderDialog();
      await page
        .getByRole("button", { name: enMain.saveDialog.allImages })
        .click();
      expect(await page.getByRole("textbox").all()).toHaveLength(0);
    });

    it("shows the image name field again when switching back to Current Image mode", async () => {
      renderDialog();
      await page
        .getByRole("button", { name: enMain.saveDialog.allImages })
        .click();
      await page
        .getByRole("button", { name: enMain.saveDialog.currentImage })
        .click();
      await expect.element(page.getByRole("textbox")).toBeVisible();
    });
  });

  describe("individual mode – label validation", () => {
    beforeEach(() => setStore([makeImage(0)]));

    it("shows a required error when saving with an empty label", async () => {
      renderDialog();
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await expect
        .element(page.getByText(enMain.saveDialog.labelRequired))
        .toBeVisible();
    });

    it("shows an invalid-chars error when the label contains special characters", async () => {
      renderDialog();
      await userEvent
        .setup()
        .type(page.getByRole("textbox").element() as HTMLElement, "bad@label");
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await expect
        .element(page.getByText(enMain.saveDialog.labelInvalid))
        .toBeVisible();
    });

    it("clears the label error as soon as the user types", async () => {
      renderDialog();
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await expect
        .element(page.getByText(enMain.saveDialog.labelRequired))
        .toBeVisible();
      await userEvent
        .setup()
        .type(page.getByRole("textbox").element() as HTMLElement, "x");
      expect(
        await page.getByText(enMain.saveDialog.labelRequired).all(),
      ).toHaveLength(0);
    });

    it("does not call saveAs when the label is empty", async () => {
      renderDialog();
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      expect(mockSaveAs).not.toHaveBeenCalled();
    });
  });

  describe("individual mode – saving", () => {
    const img = makeImage(0);

    beforeEach(() => setStore([img], img));

    it("calls saveAs with the correct PNG filename and closes the dialog", async () => {
      renderDialog();
      await userEvent
        .setup()
        .type(page.getByRole("textbox").element() as HTMLElement, "my-photo");
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await vi.waitFor(() =>
        expect(mockSaveAs).toHaveBeenCalledWith(
          img.src,
          expect.stringMatching(/^my-photo-\d{4}-\d{1,2}-\d{1,2}\.png$/),
        ),
      );
      await vi.waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    });

    it("trims surrounding whitespace from the image label before saving", async () => {
      renderDialog();
      await userEvent
        .setup()
        .type(
          page.getByRole("textbox").element() as HTMLElement,
          "  my-photo  ",
        );
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await vi.waitFor(() =>
        expect(mockSaveAs).toHaveBeenCalledWith(
          img.src,
          expect.stringMatching(/^my-photo-\d{4}-\d{1,2}-\d{1,2}\.png$/),
        ),
      );
    });

    it("uses the jpeg extension when JPEG format is selected", async () => {
      renderDialog();
      await page.getByRole("combobox").click();
      await page.getByRole("option", { name: "JPEG" }).click();
      await userEvent
        .setup()
        .type(page.getByRole("textbox").element() as HTMLElement, "my-photo");
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await vi.waitFor(() =>
        expect(mockSaveAs).toHaveBeenCalledWith(
          img.src,
          expect.stringMatching(/^my-photo-\d{4}-\d{1,2}-\d{1,2}\.jpeg$/),
        ),
      );
    });
  });

  describe("individual mode – missing current image", () => {
    beforeEach(() => setStoreWithoutCurrentImage([makeImage(0)]));

    it("does not call saveAs or close when no current image is available", async () => {
      renderDialog();
      await userEvent
        .setup()
        .type(page.getByRole("textbox").element() as HTMLElement, "my-photo");
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await vi.waitFor(() => {
        expect(mockSaveAs).not.toHaveBeenCalled();
        expect(onClose).not.toHaveBeenCalled();
      });
    });
  });

  describe("all images (ZIP) mode – saving", () => {
    const images = [
      makeImage(0, "data:image/png;base64,aaa"),
      makeImage(1, "data:image/png;base64,bbb"),
    ];

    beforeEach(() => setStore(images, images[0]));

    it("calls saveAs with a zip blob and a dated filename", async () => {
      renderDialog();
      await page
        .getByRole("button", { name: enMain.saveDialog.allImages })
        .click();
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await vi.waitFor(() =>
        expect(mockSaveAs).toHaveBeenCalledWith(
          expect.any(Blob),
          expect.stringMatching(/^nachet-mini-\d{4}-\d{1,2}-\d{1,2}\.zip$/),
        ),
      );
    });

    it("adds one zip entry per image", async () => {
      renderDialog();
      await page
        .getByRole("button", { name: enMain.saveDialog.allImages })
        .click();
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await vi.waitFor(() => expect(zipMock.file).toHaveBeenCalledTimes(2));
    });

    it("strips the data URL prefix when adding images to the zip", async () => {
      renderDialog();
      await page
        .getByRole("button", { name: enMain.saveDialog.allImages })
        .click();
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await vi.waitFor(() => expect(zipMock.file).toHaveBeenCalled());
      expect(zipMock.file).toHaveBeenCalledWith(
        expect.stringMatching(/^Capture-0-/),
        "aaa",
        { base64: true },
      );
    });

    it("closes after saving the zip", async () => {
      renderDialog();
      await page
        .getByRole("button", { name: enMain.saveDialog.allImages })
        .click();
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await vi.waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    });
  });

  describe("close and cancel behavior", () => {
    it("calls onClose when the close button is clicked", async () => {
      renderDialog();
      await page.getByRole("button", { name: "close" }).click();
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("calls onClose when the Cancel button is clicked", async () => {
      renderDialog();
      await page.getByRole("button", { name: enCommon.actions.cancel }).click();
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("resets the label to empty when Cancel is clicked", async () => {
      setStore([makeImage(0)]);
      renderDialog();
      await userEvent
        .setup()
        .type(page.getByRole("textbox").element() as HTMLElement, "abc");
      await expect.element(page.getByRole("textbox")).toHaveValue("abc");
      await page.getByRole("button", { name: enCommon.actions.cancel }).click();
      await expect.element(page.getByRole("textbox")).toHaveValue("");
    });

    it("resets to individual mode when Cancel is clicked", async () => {
      renderDialog();
      await page
        .getByRole("button", { name: enMain.saveDialog.allImages })
        .click();
      expect(await page.getByRole("textbox").all()).toHaveLength(0);
      await page.getByRole("button", { name: enCommon.actions.cancel }).click();
      await expect.element(page.getByRole("textbox")).toBeVisible();
    });

    it("resets format and label error when Cancel is clicked", async () => {
      setStore([makeImage(0)]);
      const view = renderDialog();

      await page.getByRole("combobox").click();
      await page.getByRole("option", { name: "JPEG" }).click();
      await page.getByRole("button", { name: enCommon.actions.save }).click();
      await expect
        .element(page.getByText(enMain.saveDialog.labelRequired))
        .toBeVisible();

      await page.getByRole("button", { name: enCommon.actions.cancel }).click();

      view.rerender(
        <I18nextProvider i18n={i18n}>
          <SaveDialog open={false} onClose={onClose} />
        </I18nextProvider>,
      );
      view.rerender(
        <I18nextProvider i18n={i18n}>
          <SaveDialog open onClose={onClose} />
        </I18nextProvider>,
      );

      expect(
        await page.getByText(enMain.saveDialog.labelRequired).all(),
      ).toHaveLength(0);
      await expect.element(page.getByRole("textbox")).toHaveValue("");
      expect(page.getByRole("combobox").element().textContent).toContain("PNG");
      await expect
        .element(
          page.getByRole("button", { name: enMain.saveDialog.currentImage }),
        )
        .toHaveAttribute("aria-pressed", "true");
    });
  });

  describe("i18n", () => {
    it("shows the French dialog title in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      await expect
        .element(page.getByText(frMain.saveDialog.title))
        .toBeVisible();
    });

    it("shows the French Cancel button label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: frCommon.actions.cancel }))
        .toBeVisible();
    });

    it("shows the French Current Image toggle label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      await expect
        .element(
          page.getByRole("button", {
            name: frMain.saveDialog.currentImage,
          }),
        )
        .toBeVisible();
    });
  });
});
