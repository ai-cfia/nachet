import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import frMain from "../../locales/fr/main";
import { useMetadataDefaultsStore } from "@stores/useMetadataDefaultsStore";
import { useImageStore } from "@stores/useImageStore";
import MetadataDialog from "../MetadataDialog";

vi.mock("@stores/useMetadataDefaultsStore", () => ({
  useMetadataDefaultsStore: vi.fn(),
}));
vi.mock("@stores/useImageStore", () => ({ useImageStore: vi.fn() }));

type MetadataDefaultsState = ReturnType<
  (typeof useMetadataDefaultsStore)["getState"]
>;
type ImageStoreState = ReturnType<(typeof useImageStore)["getState"]>;

const makeImage = (
  index: number,
  overrides: Partial<{
    imageName: string;
    deviceBrandId: string;
    deviceModelId: string;
    deviceLensId: string;
    trayCode: string;
    description: string;
  }> = {},
) => ({
  index,
  src: "data:image/png;base64,abc",
  imageDims: [800, 600],
  metadata: {
    imageName: overrides.imageName ?? `image-${index}.png`,
    deviceBrandId: overrides.deviceBrandId ?? "",
    deviceModelId: overrides.deviceModelId ?? "",
    deviceLensId: overrides.deviceLensId ?? "",
    trayCode: overrides.trayCode ?? "",
    description: overrides.description ?? "",
  },
  sha256: "",
});

const mockSetDefaults = vi.fn();
const mockUpdateImageMetadata = vi.fn();

const SELECT_IDS = {
  deviceBrand: "metadata-device-brand",
  deviceModel: "metadata-device-model",
  deviceLens: "metadata-device-lens",
  trayCode: "metadata-tray-code",
} as const;

const setDefaultsStore = (
  defaults: Partial<MetadataDefaultsState["defaults"]> = {},
) => {
  const fullDefaults: MetadataDefaultsState["defaults"] = {
    namePrefix: "image",
    deviceBrandId: "",
    deviceModelId: "",
    deviceLensId: "",
    trayCode: "",
    description: "",
    ...defaults,
  };
  vi.mocked(useMetadataDefaultsStore).mockImplementation(
    (selector: (state: MetadataDefaultsState) => unknown) =>
      selector({
        defaults: fullDefaults,
        setDefaults: mockSetDefaults,
        clearDefaults: vi.fn(),
      } as unknown as MetadataDefaultsState),
  );
};

const setImageStore = (
  images: ReturnType<typeof makeImage>[] = [],
  currentIndex = 0,
) => {
  vi.mocked(useImageStore).mockImplementation(
    (selector: (state: ImageStoreState) => unknown) =>
      selector({
        images,
        currentIndex,
        updateImageMetadata: mockUpdateImageMetadata,
        getCurrentImage: vi.fn().mockReturnValue(images[currentIndex]),
      } as unknown as ImageStoreState),
  );
};

type DialogRenderProps = {
  open?: boolean;
  mode?: "defaults" | "image";
  imageIndex?: number;
  onClose?: () => void;
};

const renderDialogElement = (props: DialogRenderProps, onClose: () => void) => (
  <I18nextProvider i18n={i18n}>
    <MetadataDialog
      open={props.open ?? true}
      onClose={onClose}
      mode={props.mode ?? "defaults"}
      imageIndex={props.imageIndex}
    />
  </I18nextProvider>
);

const renderDialog = (props: DialogRenderProps = {}) => {
  const onClose = props.onClose ?? vi.fn();
  let currentProps = props;
  const view = render(renderDialogElement(currentProps, onClose));

  return {
    onClose,
    rerenderDialog: (nextProps: DialogRenderProps = {}) => {
      currentProps = { ...currentProps, ...nextProps, onClose };
      view.rerender(renderDialogElement(currentProps, onClose));
    },
    ...view,
  };
};

const getSelect = (testId: (typeof SELECT_IDS)[keyof typeof SELECT_IDS]) =>
  page.getByTestId(testId);

describe("MetadataDialog", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
    mockSetDefaults.mockClear();
    mockUpdateImageMetadata.mockClear();
    setDefaultsStore();
    setImageStore();
  });

  afterEach(cleanup);

  describe("when closed", () => {
    it("does not render the dialog content when open is false", async () => {
      renderDialog({ open: false });
      expect(await page.getByRole("dialog").all()).toHaveLength(0);
    });
  });

  describe("defaults mode", () => {
    it("renders the defaults title", async () => {
      renderDialog({ mode: "defaults" });
      await expect
        .element(page.getByText(enMain.metadata.defaultsTitle))
        .toBeVisible();
    });

    it("shows the name prefix field", async () => {
      renderDialog({ mode: "defaults" });
      await expect
        .element(
          page.getByRole("textbox", { name: enMain.metadata.namePrefix }),
        )
        .toBeVisible();
    });

    it("initializes name prefix from store defaults", async () => {
      setDefaultsStore({ namePrefix: "my-prefix" });
      renderDialog({ mode: "defaults" });
      await expect
        .element(
          page.getByRole("textbox", { name: enMain.metadata.namePrefix }),
        )
        .toHaveValue("my-prefix");
    });

    it("does not show an image name field", async () => {
      renderDialog({ mode: "defaults" });
      expect(
        await page
          .getByRole("textbox", { name: enMain.metadata.imageName })
          .all(),
      ).toHaveLength(0);
    });

    it("shows a validation error when saving with an empty name prefix", async () => {
      setDefaultsStore({ namePrefix: "" });
      renderDialog({ mode: "defaults" });
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await expect
        .element(page.getByText(enMain.metadata.validation.imageNameRequired))
        .toBeVisible();
    });

    it("clears the name prefix error when the user types", async () => {
      setDefaultsStore({ namePrefix: "" });
      renderDialog({ mode: "defaults" });
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await expect
        .element(page.getByText(enMain.metadata.validation.imageNameRequired))
        .toBeVisible();

      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.namePrefix })
            .element() as HTMLElement,
          "x",
        );
      expect(
        await page
          .getByText(enMain.metadata.validation.imageNameRequired)
          .all(),
      ).toHaveLength(0);
    });

    it("shows a validation error for an invalid name prefix", async () => {
      setDefaultsStore({ namePrefix: "" });
      renderDialog({ mode: "defaults" });
      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.namePrefix })
            .element() as HTMLElement,
          "bad name!",
        );
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await expect
        .element(page.getByText(enMain.metadata.validation.imageNameInvalid))
        .toBeVisible();
    });

    it("calls setDefaults with correct values on save", async () => {
      setDefaultsStore({ namePrefix: "" });
      renderDialog({ mode: "defaults" });
      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.namePrefix })
            .element() as HTMLElement,
          "my-prefix",
        );
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await vi.waitFor(() =>
        expect(mockSetDefaults).toHaveBeenCalledWith(
          expect.objectContaining({ namePrefix: "my-prefix" }),
        ),
      );
    });

    it("saves the full defaults payload", async () => {
      setDefaultsStore({ namePrefix: "", description: "" });
      renderDialog({ mode: "defaults" });

      const user = userEvent.setup();
      await user.type(
        page
          .getByRole("textbox", { name: enMain.metadata.namePrefix })
          .element() as HTMLElement,
        "specimen-2026",
      );
      await getSelect(SELECT_IDS.deviceBrand).click();
      await page.getByRole("option", { name: "Tagarno" }).click();
      await getSelect(SELECT_IDS.deviceModel).click();
      await page.getByRole("option", { name: "Prestige" }).click();
      await getSelect(SELECT_IDS.deviceLens).click();
      await page.getByRole("option", { name: "3x" }).click();
      await getSelect(SELECT_IDS.trayCode).click();
      await page.getByRole("option", { name: "B", exact: true }).click();
      await user.type(
        page
          .getByRole("textbox", { name: enMain.metadata.description })
          .element() as HTMLElement,
        "Microscope capture 42.",
      );

      await page.getByRole("button", { name: enMain.metadata.save }).click();

      await vi.waitFor(() =>
        expect(mockSetDefaults).toHaveBeenCalledWith({
          namePrefix: "specimen-2026",
          deviceBrandId: "tagarno",
          deviceModelId: "prestige",
          deviceLensId: "3x",
          trayCode: "B",
          description: "Microscope capture 42.",
        }),
      );
    });

    it("closes the dialog after a successful save", async () => {
      const onClose = vi.fn();
      renderDialog({ mode: "defaults", onClose });
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await vi.waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    });

    it("does not call setDefaults when validation fails", async () => {
      setDefaultsStore({ namePrefix: "" });
      renderDialog({ mode: "defaults" });
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      expect(mockSetDefaults).not.toHaveBeenCalled();
    });
  });

  describe("image mode", () => {
    it("renders the image title", async () => {
      setImageStore([makeImage(0)]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await expect
        .element(page.getByText(enMain.metadata.imageTitle))
        .toBeVisible();
    });

    it("shows the image name field", async () => {
      setImageStore([makeImage(0)]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await expect
        .element(page.getByRole("textbox", { name: enMain.metadata.imageName }))
        .toBeVisible();
    });

    it("does not show a name prefix field", async () => {
      setImageStore([makeImage(0)]);
      renderDialog({ mode: "image", imageIndex: 0 });
      expect(
        await page
          .getByRole("textbox", { name: enMain.metadata.namePrefix })
          .all(),
      ).toHaveLength(0);
    });

    it("initializes image name from the image metadata", async () => {
      setImageStore([makeImage(0, { imageName: "existing-name.png" })]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await expect
        .element(page.getByRole("textbox", { name: enMain.metadata.imageName }))
        .toHaveValue("existing-name.png");
    });

    it("shows a required error when saving with an empty image name", async () => {
      setImageStore([makeImage(0, { imageName: "" })]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await expect
        .element(page.getByText(enMain.metadata.validation.imageNameRequired))
        .toBeVisible();
    });

    it("shows an invalid error for an image name with forbidden characters", async () => {
      setImageStore([makeImage(0, { imageName: "" })]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.imageName })
            .element() as HTMLElement,
          "bad name!",
        );
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await expect
        .element(page.getByText(enMain.metadata.validation.imageNameInvalid))
        .toBeVisible();
    });

    it("clears the image name error when the user types", async () => {
      setImageStore([makeImage(0, { imageName: "" })]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await expect
        .element(page.getByText(enMain.metadata.validation.imageNameRequired))
        .toBeVisible();

      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.imageName })
            .element() as HTMLElement,
          "x",
        );
      expect(
        await page
          .getByText(enMain.metadata.validation.imageNameRequired)
          .all(),
      ).toHaveLength(0);
    });

    it("calls updateImageMetadata with correct values on save", async () => {
      setImageStore([makeImage(0, { imageName: "" })]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.imageName })
            .element() as HTMLElement,
          "my-photo",
        );
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await vi.waitFor(() =>
        expect(mockUpdateImageMetadata).toHaveBeenCalledWith(
          0,
          expect.objectContaining({ imageName: "my-photo" }),
        ),
      );
    });

    it("saves the full image metadata payload", async () => {
      setImageStore([makeImage(0, { imageName: "", description: "" })]);
      renderDialog({ mode: "image", imageIndex: 0 });

      const user = userEvent.setup();
      await user.type(
        page
          .getByRole("textbox", { name: enMain.metadata.imageName })
          .element() as HTMLElement,
        "capture-007",
      );
      await getSelect(SELECT_IDS.deviceBrand).click();
      await page.getByRole("option", { name: "Tagarno" }).click();
      await getSelect(SELECT_IDS.deviceModel).click();
      await page.getByRole("option", { name: "Prestige" }).click();
      await getSelect(SELECT_IDS.deviceLens).click();
      await page.getByRole("option", { name: "4x" }).click();
      await getSelect(SELECT_IDS.trayCode).click();
      await page.getByRole("option", { name: "C", exact: true }).click();
      await user.type(
        page
          .getByRole("textbox", { name: enMain.metadata.description })
          .element() as HTMLElement,
        "Detailed specimen overview.",
      );

      await page.getByRole("button", { name: enMain.metadata.save }).click();

      await vi.waitFor(() =>
        expect(mockUpdateImageMetadata).toHaveBeenCalledWith(0, {
          imageName: "capture-007",
          deviceBrandId: "tagarno",
          deviceModelId: "prestige",
          deviceLensId: "4x",
          trayCode: "C",
          description: "Detailed specimen overview.",
        }),
      );
    });

    it("closes the dialog after a successful save", async () => {
      const onClose = vi.fn();
      setImageStore([makeImage(0, { imageName: "valid-name.png" })]);
      renderDialog({ mode: "image", imageIndex: 0, onClose });
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await vi.waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    });

    it("does not call updateImageMetadata when validation fails", async () => {
      setImageStore([makeImage(0, { imageName: "" })]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      expect(mockUpdateImageMetadata).not.toHaveBeenCalled();
    });
  });

  // MUI Select renders comboboxes without resolvable accessible names via aria-labelledby
  // in the Playwright test environment, so we target stable test ids instead.
  describe("device brand selection", () => {
    it("renders the device brand select", async () => {
      renderDialog({ mode: "defaults" });
      await expect.element(getSelect(SELECT_IDS.deviceBrand)).toBeVisible();
    });

    it("device model and lens selects are disabled when no brand is selected", async () => {
      renderDialog({ mode: "defaults" });
      await expect
        .element(getSelect(SELECT_IDS.deviceModel))
        .toHaveAttribute("aria-disabled", "true");
      await expect
        .element(getSelect(SELECT_IDS.deviceLens))
        .toHaveAttribute("aria-disabled", "true");
    });

    it("enables device model and lens selects after selecting a brand", async () => {
      renderDialog({ mode: "defaults" });
      await getSelect(SELECT_IDS.deviceBrand).click();
      await page.getByRole("option", { name: "Tagarno" }).click();
      await vi.waitFor(() =>
        expect(
          getSelect(SELECT_IDS.deviceModel)
            .element()
            .getAttribute("aria-disabled"),
        ).not.toBe("true"),
      );
      await vi.waitFor(() =>
        expect(
          getSelect(SELECT_IDS.deviceLens)
            .element()
            .getAttribute("aria-disabled"),
        ).not.toBe("true"),
      );
    });

    it("resets model and lens when brand changes", async () => {
      setDefaultsStore({
        deviceBrandId: "tagarno",
        deviceModelId: "prestige",
        deviceLensId: "3x",
      });
      renderDialog({ mode: "defaults" });
      await getSelect(SELECT_IDS.deviceBrand).click();
      await page.getByRole("option", { name: "None" }).click();
      await vi.waitFor(() =>
        expect(
          getSelect(SELECT_IDS.deviceModel).element().textContent,
        ).not.toContain("Prestige"),
      );
      await vi.waitFor(() =>
        expect(
          getSelect(SELECT_IDS.deviceLens).element().textContent,
        ).not.toContain("3x"),
      );
    });

    it("includes device brand in saved defaults", async () => {
      renderDialog({ mode: "defaults" });
      await getSelect(SELECT_IDS.deviceBrand).click();
      await page.getByRole("option", { name: "Tagarno" }).click();
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await vi.waitFor(() =>
        expect(mockSetDefaults).toHaveBeenCalledWith(
          expect.objectContaining({ deviceBrandId: "tagarno" }),
        ),
      );
    });
  });

  describe("tray code selection", () => {
    it("renders the tray code select", async () => {
      renderDialog({ mode: "defaults" });
      await expect.element(getSelect(SELECT_IDS.trayCode)).toBeVisible();
    });

    it("includes tray code in saved defaults when selected", async () => {
      renderDialog({ mode: "defaults" });
      await getSelect(SELECT_IDS.trayCode).click();
      await page.getByRole("option", { name: "A", exact: true }).click();
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await vi.waitFor(() =>
        expect(mockSetDefaults).toHaveBeenCalledWith(
          expect.objectContaining({ trayCode: "A" }),
        ),
      );
    });
  });

  describe("description field", () => {
    it("renders the description text area", async () => {
      renderDialog({ mode: "defaults" });
      await expect
        .element(
          page.getByRole("textbox", { name: enMain.metadata.description }),
        )
        .toBeVisible();
    });

    it("shows a validation error for an invalid description", async () => {
      renderDialog({ mode: "defaults" });
      // $ is not in the allowed character set for descriptions
      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.description })
            .element() as HTMLElement,
          "bad$description",
        );
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await expect
        .element(page.getByText(enMain.metadata.validation.descriptionInvalid))
        .toBeVisible();
    });

    it("clears the description error when the user edits the field", async () => {
      renderDialog({ mode: "defaults" });
      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.description })
            .element() as HTMLElement,
          "bad$desc",
        );
      await page.getByRole("button", { name: enMain.metadata.save }).click();
      await expect
        .element(page.getByText(enMain.metadata.validation.descriptionInvalid))
        .toBeVisible();

      await userEvent
        .setup()
        .clear(
          page
            .getByRole("textbox", { name: enMain.metadata.description })
            .element() as HTMLElement,
        );
      expect(
        await page
          .getByText(enMain.metadata.validation.descriptionInvalid)
          .all(),
      ).toHaveLength(0);
    });
  });

  describe("cancel behavior", () => {
    it("calls onClose when Cancel is clicked", async () => {
      const onClose = vi.fn();
      renderDialog({ onClose });
      await page.getByRole("button", { name: enMain.metadata.cancel }).click();
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("does not call setDefaults when Cancel is clicked", async () => {
      renderDialog({ mode: "defaults" });
      await userEvent
        .setup()
        .type(
          page
            .getByRole("textbox", { name: enMain.metadata.namePrefix })
            .element() as HTMLElement,
          "-extra",
        );
      await page.getByRole("button", { name: enMain.metadata.cancel }).click();
      expect(mockSetDefaults).not.toHaveBeenCalled();
    });

    it("resets the form state after close and reopen", async () => {
      setDefaultsStore({
        namePrefix: "stored-prefix",
        deviceBrandId: "tagarno",
        deviceModelId: "prestige",
        deviceLensId: "3x",
        trayCode: "D",
        description: "Stored defaults",
      });
      const view = renderDialog({ mode: "defaults" });
      const user = userEvent.setup();

      await user.clear(
        page
          .getByRole("textbox", { name: enMain.metadata.namePrefix })
          .element() as HTMLElement,
      );
      await user.type(
        page
          .getByRole("textbox", { name: enMain.metadata.namePrefix })
          .element() as HTMLElement,
        "edited-prefix",
      );
      await getSelect(SELECT_IDS.deviceBrand).click();
      await page.getByRole("option", { name: "None" }).click();
      await getSelect(SELECT_IDS.trayCode).click();
      await page.getByRole("option", { name: "A", exact: true }).click();
      await user.clear(
        page
          .getByRole("textbox", { name: enMain.metadata.description })
          .element() as HTMLElement,
      );
      await user.type(
        page
          .getByRole("textbox", { name: enMain.metadata.description })
          .element() as HTMLElement,
        "Unsaved edits",
      );
      await page.getByRole("button", { name: enMain.metadata.cancel }).click();

      view.rerenderDialog({ open: false });
      view.rerenderDialog({ open: true });

      await expect
        .element(
          page.getByRole("textbox", { name: enMain.metadata.namePrefix }),
        )
        .toHaveValue("stored-prefix");
      await expect
        .element(
          page.getByRole("textbox", { name: enMain.metadata.description }),
        )
        .toHaveValue("Stored defaults");
      await vi.waitFor(() =>
        expect(
          getSelect(SELECT_IDS.deviceBrand).element().textContent,
        ).toContain("Tagarno"),
      );
      await vi.waitFor(() =>
        expect(
          getSelect(SELECT_IDS.deviceModel).element().textContent,
        ).toContain("Prestige"),
      );
      await vi.waitFor(() =>
        expect(
          getSelect(SELECT_IDS.deviceLens).element().textContent,
        ).toContain("3x"),
      );
      await vi.waitFor(() =>
        expect(getSelect(SELECT_IDS.trayCode).element().textContent).toContain(
          "D",
        ),
      );
    });
  });

  describe("i18n", () => {
    it("shows the French defaults title in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog({ mode: "defaults" });
      await expect
        .element(page.getByText(frMain.metadata.defaultsTitle))
        .toBeVisible();
    });

    it("shows the French image title in French mode", async () => {
      await i18n.changeLanguage("fr");
      setImageStore([makeImage(0)]);
      renderDialog({ mode: "image", imageIndex: 0 });
      await expect
        .element(page.getByText(frMain.metadata.imageTitle))
        .toBeVisible();
    });

    it("shows the French Cancel button label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog({ mode: "defaults" });
      await expect
        .element(page.getByRole("button", { name: frMain.metadata.cancel }))
        .toBeVisible();
    });

    it("shows the French Save button label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog({ mode: "defaults" });
      await expect
        .element(page.getByRole("button", { name: frMain.metadata.save }))
        .toBeVisible();
    });
  });
});
