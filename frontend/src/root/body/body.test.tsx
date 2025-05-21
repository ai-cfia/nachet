import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Body from "./body";

process.env.VITE_BACKEND_URL = "somebackendurl";

vi.mock("../../common", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../common")>();
  return {
    ...mod,
    readAzureStorageDir: vi.fn(() => {
      return Promise.resolve({
        testDir1: 0,
        testDir2: 1,
        testDir3: 2,
      });
    }),
    createAzureStorageDir: vi.fn(),
    deleteAzureStorageDir: vi.fn(),
    inferenceRequest: vi.fn(),
    fetchModelMetadata: vi.fn(() => {
      return Promise.resolve([
        {
          created_by: "Wayne Gretzky",
          creation_date: "2023-12-01",
          dataset: "",
          default: false,
          description:
            "trained using 6 seed images per image of 14of15 tagarno",
          job_name: "neat_cartoon_k0y4m0vz",
          model_name: "9000 Seed Detector",
          models: ["m-14of15seeds-6seedsmag"],
          pipeline_id: "123",
          pipeline_name: "9000 Seed Detector",
          version: "1",
        },
      ]);
    }),
    requestClassList: vi.fn(() => {
      return Promise.resolve({
        seeds: [
          {
            seed_id: "1",
            seed_name: "seed_name1",
          },
          {
            seed_id: "2",
            seed_name: "seed_name2",
          },
          {
            seed_id: "3",
            seed_name: "seed_name3",
          },
        ],
      });
    }),
    requestUUID: vi.fn(() => {
      return Promise.resolve({
        uuid: "1234",
      });
    }),
  };
});
const mockProps = {
  windowSize: {
    width: 1000,
    height: 1000,
  },
  uuid: "1234",
  creativeCommonsPopupOpen: false,
  setCreativeCommonsPopupOpen: vi.fn(),
  handleCreativeCommonsAgreement: vi.fn(),
  setSignUpOpen: vi.fn(),
  signUpOpen: false,
  signedIn: false,
  setSignedIn: vi.fn(),
  setUuid: vi.fn(),
};

const mockAddEventListener = vi.fn();
const mockGetUserMedia = vi.fn(async () => {
  return new Promise<void>((resolve) => {
    resolve();
  });
});

Object.defineProperty(global.navigator, "mediaDevices", {
  value: {
    addEventListener: mockAddEventListener,
    removeEventListener: vi.fn(),
    getUserMedia: mockGetUserMedia,
  },
});

Object.defineProperty(global.window, "alert", {
  value: vi.fn(),
});

describe("Body", () => {
  it("renders Body component", async () => {
    render(<Body {...mockProps} />);
    const bodyElement = await screen.findByTestId("body-component");
    expect(bodyElement).toBeTruthy();
  });

  it("renders Microscope Feed", async () => {
    render(<Body {...mockProps} />);
    const classifierElement = await screen.findByTestId("microscope-component");
    expect(classifierElement).toBeTruthy();
  });

  it("renders Storage Directory", async () => {
    render(<Body {...mockProps} />);
    const storageElement = await screen.findByTestId(
      "storage-directory-component",
    );
    expect(storageElement).toBeTruthy();
  });

  it("renders Image Cache", async () => {
    render(<Body {...mockProps} />);
    const imageCacheElement = await screen.findByTestId(
      "image-cache-component",
    );
    expect(imageCacheElement).toBeTruthy();
  });

  it("renders Classification Results", async () => {
    render(<Body {...mockProps} />);
    const classificationResultsElement = await screen.findByTestId(
      "classification-results-component",
    );
    expect(classificationResultsElement).toBeTruthy();
  });

  // TODO: test the popups
});
