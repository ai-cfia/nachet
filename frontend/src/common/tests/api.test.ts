import { describe, it, vi } from "vitest";
import {
  createAzureStorageDir,
  deleteAzureStorageDir,
  fetchModelMetadata,
  inferenceRequest,
  readAzureStorageDir,
} from "../api";
import axios from "axios";
import { AzureAPIError } from "../error";

// mock axios
vi.mock("axios");
const mockedAxios = vi.mocked(axios);

describe("readAzureStorageDir", () => {
  it("should return data", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: "data",
    });
    const backendUrl = "backendUrl";
    const uuid = "uuid";

    expect(await readAzureStorageDir(backendUrl, uuid)).toEqual("data");
  });

  it("should throw error has response", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "error",
        status: 400,
      },
    });
    const backendUrl = "backendUrl";
    const uuid = "uuid";

    await expect(readAzureStorageDir(backendUrl, uuid)).rejects.toEqual(
      new AzureAPIError("error"),
    );
    expect(console.error).toHaveBeenCalled();
    console.error = consoleError;
  });

  it("should throw error has request", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      request: "error",
    });
    const backendUrl = "backendUrl";
    const uuid = "uuid";

    await expect(readAzureStorageDir(backendUrl, uuid)).rejects.toEqual(
      new AzureAPIError("error"),
    );
    expect(console.error).toHaveBeenCalled();
    console.error = consoleError;
  });

  it("should show console error has message", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      message: "error",
      config: "config",
    });
    const backendUrl = "backendUrl";
    const uuid = "uuid";

    await expect(readAzureStorageDir(backendUrl, uuid)).rejects.toEqual(
      new AzureAPIError("config"),
    );
    expect(console.error).toHaveBeenCalled();
    console.error = consoleError;
  });

  it("should throw error has config", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      config: "error",
    });
    const backendUrl = "backendUrl";
    const uuid = "uuid";

    await expect(readAzureStorageDir(backendUrl, uuid)).rejects.toEqual(
      new AzureAPIError("error"),
    );
    expect(console.error).toHaveBeenCalled();
    console.error = consoleError;
  });
});

describe("createAzureStorageDir", () => {
  it("should return data", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: "data",
    });
    const backendUrl = "backendUrl";
    const uuid = "uuid";
    const folderName = "folderName";

    expect(await createAzureStorageDir(backendUrl, uuid, folderName)).toEqual(
      "data",
    );
  });
});

describe("deleteAzureStorageDir", () => {
  it("should return data", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: "data",
    });
    const backendUrl = "backendUrl";
    const uuid = "uuid";
    const folderName = "folderName";

    expect(await deleteAzureStorageDir(backendUrl, uuid, folderName)).toEqual(
      "data",
    );
  });
});

describe("inferenceRequest", () => {
  it("should return data", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: "data",
    });

    const backendUrl = "backendUrl";
    const uuid = "uuid";
    const imageObject = {
      index: 0,
      src: "test",
      scores: [],
      classifications: [],
      boxes: [],
      annotated: false,
      imageDims: [0, 0],
      overlapping: [],
      overlappingIndices: [],
      topN: [],
    };
    const curDir = "curDir";
    const selectedModel = "swin";

    expect(
      await inferenceRequest(
        backendUrl,
        selectedModel,
        imageObject,
        curDir,
        uuid,
        uuid,
      ),
    ).toEqual("data");
  });
});

describe("fetchModelMetadata", () => {
  it("should return number", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: "data",
    });

    const backendUrl = "backendUrl";

    expect(await fetchModelMetadata(backendUrl)).toEqual("data");
  });
});
