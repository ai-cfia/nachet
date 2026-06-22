import { describe, it, vi, beforeEach, expect } from "vitest";
import {
  createAzureStorageDir,
  deleteAzureStorageDir,
  fetchDevices,
  fetchModelMetadata,
  inferenceRequest,
  readAzureStorageDir,
  sendPositiveFeedback,
  sendNegativeFeedback,
  sendFeedbackNewBox,
  requestClassList,
  batchUploadInit,
  batchUploadImage,
} from "../api";
import axios from "axios";
import { AzureAPIError, ValueError } from "../error";

// mock axios
vi.mock("axios");
const mockedAxios = vi.mocked(axios);

// mock errorLogger
vi.mock("../../logging", () => ({
  errorLogger: {
    getCorrelationId: vi.fn(() => "test-correlation-id"),
    getSessionId: vi.fn(() => "test-session-id"),
    setCorrelationId: vi.fn(),
    logError: vi.fn(),
    logWarning: vi.fn(),
    logInfo: vi.fn(),
    logApiError: vi.fn(),
  },
}));

beforeEach(() => {
  mockedAxios.mockClear();
});

describe("protected API auth initialization", () => {
  it("should fail closed before sending protected requests without auth initialization", async () => {
    await expect(
      fetchDevices({ backendUrl: "http://localhost:8080" }),
    ).rejects.toThrow(
      new ValueError("Auth provider is not initialized for API requests"),
    );

    expect(mockedAxios).not.toHaveBeenCalled();
  });
});

describe("readAzureStorageDir", () => {
  it("should return data on success", async () => {
    const mockData = {
      directories: [
        {
          id: "set-123",
          name: "test-folder",
          folderPrefix: "test-prefix",
          description: "Test folder description",
          pictureCount: 5,
        },
      ],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockData,
    });
    const backendUrl = "http://localhost:8080";
    const accessToken = "valid-access-token";

    const result = await readAzureStorageDir({ backendUrl, accessToken });
    expect(result).toEqual(mockData);
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "get",
      url: `${backendUrl}/get-directories`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer ${accessToken}`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      readAzureStorageDir({ backendUrl: "", accessToken: "valid-token" }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for null backend URL", async () => {
    await expect(
      readAzureStorageDir({
        backendUrl: null as any,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty access token", async () => {
    await expect(
      readAzureStorageDir({
        backendUrl: "http://localhost:8080",
        accessToken: "",
      }),
    ).rejects.toThrow(new ValueError("Access token is null or empty"));
  });

  it("should throw ValueError for null access token", async () => {
    await expect(
      readAzureStorageDir({
        backendUrl: "http://localhost:8080",
        accessToken: null as any,
      }),
    ).rejects.toThrow(new ValueError("Access token is null or empty"));
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
    const accessToken = "valid-token";

    await expect(
      readAzureStorageDir({ backendUrl, accessToken }),
    ).rejects.toEqual(new AzureAPIError("error"));
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
    const accessToken = "valid-token";

    await expect(
      readAzureStorageDir({ backendUrl, accessToken }),
    ).rejects.toEqual(new AzureAPIError("Network request failed"));
    expect(console.error).toHaveBeenCalled();
    console.error = consoleError;
  });

  it("should handle generic error with message", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      message: "Network error",
      config: "error config",
    });
    const backendUrl = "http://localhost:8080";
    const accessToken = "valid-token";

    await expect(
      readAzureStorageDir({ backendUrl, accessToken }),
    ).rejects.toEqual(new AzureAPIError("Network error"));
    expect(console.error).toHaveBeenCalledWith("Error", "Network error");
    console.error = consoleError;
  });

  it("should handle non-200 status codes", async () => {
    mockedAxios.mockResolvedValue({
      status: 201,
      data: "created",
    });
    const backendUrl = "http://localhost:8080";
    const accessToken = "valid-token";

    await expect(
      readAzureStorageDir({ backendUrl, accessToken }),
    ).rejects.toThrow(AzureAPIError);
  });

  it("should throw error has config", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      config: "error",
    });
    const backendUrl = "backendUrl";
    const accessToken = "valid-token";

    await expect(
      readAzureStorageDir({ backendUrl, accessToken }),
    ).rejects.toEqual(new AzureAPIError("Unknown error"));
    expect(console.error).toHaveBeenCalled();
    console.error = consoleError;
  });
});

describe("createAzureStorageDir", () => {
  it("should create directory successfully", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: { folderName: "test-folder" },
    });
    const backendUrl = "http://localhost:8080";
    const accessToken = "valid-token";
    const folderName = "test-folder";

    await createAzureStorageDir({ backendUrl, accessToken, folderName });
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "post",
      url: `${backendUrl}/create-dir`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer ${accessToken}`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: {
        folderName: folderName,
      },
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      createAzureStorageDir({
        backendUrl: "",
        accessToken: "valid-token",
        folderName: "folder",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty access token", async () => {
    await expect(
      createAzureStorageDir({
        backendUrl: "http://localhost:8080",
        accessToken: "",
        folderName: "folder",
      }),
    ).rejects.toThrow(new ValueError("Access token is null or empty"));
  });

  it("should throw ValueError for empty folder name", async () => {
    await expect(
      createAzureStorageDir({
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
        folderName: "",
      }),
    ).rejects.toThrow(new ValueError("Folder name is null or empty"));
  });

  it("should handle API errors", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "Permission denied",
        status: 403,
      },
    });

    await expect(
      createAzureStorageDir({
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
        folderName: "folder",
      }),
    ).rejects.toThrow(new AzureAPIError("Permission denied"));
    console.error = consoleError;
  });
});

describe("deleteAzureStorageDir", () => {
  it("should delete directory successfully", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: { folderName: "test-folder" },
    });
    const backendUrl = "http://localhost:8080";
    const accessToken = "valid-token";
    const folderName = "test-folder";

    await deleteAzureStorageDir({ backendUrl, accessToken, folderName });
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "post",
      url: `${backendUrl}/del`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer ${accessToken}`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: {
        folderName: folderName,
      },
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      deleteAzureStorageDir({
        backendUrl: "",
        accessToken: "valid-token",
        folderName: "folder",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty access token", async () => {
    await expect(
      deleteAzureStorageDir({
        backendUrl: "http://localhost:8080",
        accessToken: "",
        folderName: "folder",
      }),
    ).rejects.toThrow(new ValueError("Access token is null or empty"));
  });

  it("should throw ValueError for empty folder name", async () => {
    await expect(
      deleteAzureStorageDir({
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
        folderName: "",
      }),
    ).rejects.toThrow(new ValueError("Folder name is null or empty"));
  });

  it("should handle directory not found errors", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "Directory not found",
        status: 404,
      },
    });

    await expect(
      deleteAzureStorageDir({
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
        folderName: "nonexistent",
      }),
    ).rejects.toThrow(new AzureAPIError("Directory not found"));
    console.error = consoleError;
  });
});

describe("inferenceRequest", () => {
  const mockImageObject = {
    index: 0,
    src: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ",
    imageName: "test-image",
    imageDescription: "Test image description",
    imageDims: [640, 480],
    deviceBrandId: "12345678-1234-1234-8234-123456789012",
    deviceModelId: "22345678-1234-1234-8234-123456789012",
    deviceLensId: "32345678-1234-1234-8234-123456789012",
    trayCode: "A" as const,
    magnification: 50,
    workflowIds: [],
    activeWorkflowId: null,
  };

  it("should return inference data on success", async () => {
    const mockSubmissionResponse = {
      imageId: "img-123",
      workflowId: "wf-456",
      status: "pending",
      message: "Image submitted for processing",
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockSubmissionResponse,
    });

    const backendUrl = "http://localhost:8080";
    const folderId = "42345678-1234-1234-8234-123456789012";
    const curDir = "test-directory";
    const selectedModel = "swin-transformer";

    const result = await inferenceRequest({
      backendUrl,
      selectedModel,
      imageObject: mockImageObject,
      curDir,
      accessToken: "valid-token",
      folderId: folderId,
    });

    expect(result).toEqual(mockSubmissionResponse);
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "post",
      url: `${backendUrl}/inf`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer valid-token`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: {
        pipelineId: selectedModel,
        folderName: curDir,
        folderId: folderId,
        image: mockImageObject.src,
        imageName: mockImageObject.imageName,
        imageDescription: mockImageObject.imageDescription,
        imageDims: mockImageObject.imageDims,
        deviceBrandId: mockImageObject.deviceBrandId,
        deviceModelId: mockImageObject.deviceModelId,
        deviceLensId: mockImageObject.deviceLensId,
        trayCode: mockImageObject.trayCode,
        magnification: mockImageObject.magnification,
      },
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      inferenceRequest({
        backendUrl: "",
        selectedModel: "model",
        imageObject: mockImageObject,
        curDir: "dir",
        accessToken: "token",
        folderId: "folder-id",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty model", async () => {
    await expect(
      inferenceRequest({
        backendUrl: "http://localhost:8080",
        selectedModel: "",
        imageObject: mockImageObject,
        curDir: "dir",
        accessToken: "token",
        folderId: "folder-id",
      }),
    ).rejects.toThrow(new ValueError("Model is null or empty"));
  });

  it("should throw ValueError for empty image", async () => {
    const emptyImageObject = { ...mockImageObject, src: "" };
    await expect(
      inferenceRequest({
        backendUrl: "http://localhost:8080",
        selectedModel: "model",
        imageObject: emptyImageObject,
        curDir: "dir",
        accessToken: "token",
        folderId: "folder-id",
      }),
    ).rejects.toThrow(new ValueError("Image is null or empty"));
  });

  it("should throw ValueError for empty directory", async () => {
    await expect(
      inferenceRequest({
        backendUrl: "http://localhost:8080",
        selectedModel: "model",
        imageObject: mockImageObject,
        curDir: "",
        accessToken: "token",
        folderId: "folder-id",
      }),
    ).rejects.toThrow(new ValueError("Directory is null or empty"));
  });

  it("should throw ValueError for empty access token", async () => {
    await expect(
      inferenceRequest({
        backendUrl: "http://localhost:8080",
        selectedModel: "model",
        imageObject: mockImageObject,
        curDir: "dir",
        accessToken: "",
        folderId: "folder-id",
      }),
    ).rejects.toThrow(new ValueError("Access token is null or empty"));
  });

  it("should handle inference service errors", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "Model not available",
        status: 503,
      },
    });

    await expect(
      inferenceRequest({
        backendUrl: "http://localhost:8080",
        selectedModel: "invalid-model",
        imageObject: mockImageObject,
        curDir: "dir",
        accessToken: "token",
        folderId: "52345678-1234-1234-8234-123456789012",
      }),
    ).rejects.toThrow(new AzureAPIError("Model not available"));
    console.error = consoleError;
  });

  it("should handle invalid image format errors", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "Invalid image format",
        status: 400,
      },
    });

    await expect(
      inferenceRequest({
        backendUrl: "http://localhost:8080",
        selectedModel: "model",
        imageObject: mockImageObject,
        curDir: "dir",
        accessToken: "token",
        folderId: "62345678-1234-1234-8234-123456789012",
      }),
    ).rejects.toThrow(new AzureAPIError("Invalid image format"));
    console.error = consoleError;
  });

  it("should handle network timeout errors", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      request: "Network timeout",
    });

    await expect(
      inferenceRequest({
        backendUrl: "http://localhost:8080",
        selectedModel: "model",
        imageObject: mockImageObject,
        curDir: "dir",
        accessToken: "token",
        folderId: "72345678-1234-1234-8234-123456789012",
      }),
    ).rejects.toThrow(new AzureAPIError("Network request failed"));
    console.error = consoleError;
  });
});

describe("handleAxios error scenarios", () => {
  it("should handle non-200 status in successful response", async () => {
    mockedAxios.mockResolvedValue({
      status: 202,
      data: "accepted",
    });

    await expect(
      fetchModelMetadata({
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(AzureAPIError);
  });
});

describe("fetchModelMetadata", () => {
  it("should return model metadata on success", async () => {
    const mockMetadata = [
      {
        createdBy: "test-user",
        creationDate: "2023-12-01",
        dataset: "seed-dataset-v1",
        description: "Test model for seed detection",
        identifiable: ["wheat", "oat", "barley"],
        jobName: "test_job_123",
        metrics: ["precision: 0.95", "recall: 0.92"],
        modelName: "Seed Detector v1",
        models: ["detector-model-123"],
        pipelineName: "seed-detection-pipeline",
        pipelineId: "00000000-0000-0000-0000-000000000001",
        default: true,
      },
    ];
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockMetadata,
    });

    const backendUrl = "http://localhost:8080";
    const result = await fetchModelMetadata({
      backendUrl,
      accessToken: "valid-token",
    });

    expect(result).toEqual(mockMetadata);
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "get",
      url: `${backendUrl}/model-endpoints-metadata`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer valid-token`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: {},
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      fetchModelMetadata({ backendUrl: "", accessToken: "valid-token" }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for null backend URL", async () => {
    await expect(
      fetchModelMetadata({
        backendUrl: null as any,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should handle service unavailable errors", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "Service temporarily unavailable",
        status: 503,
      },
    });

    await expect(
      fetchModelMetadata({
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new AzureAPIError("Service temporarily unavailable"));
    console.error = consoleError;
  });

  it("should handle empty metadata response", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: [],
    });

    const result = await fetchModelMetadata({
      backendUrl: "http://localhost:8080",
      accessToken: "valid-token",
    });
    expect(result).toEqual([]);
  });
});

describe("requestClassList", () => {
  it("should return species data on success", async () => {
    const mockSpeciesData = {
      seeds: [
        {
          seedId: "1",
          nameCode: "WHEAT_001",
          family: "Poaceae",
          genus: "Triticum",
          species: "aestivum",
        },
        {
          seedId: "2",
          nameCode: "OAT_001",
          family: "Poaceae",
          genus: "Avena",
          species: "sativa",
        },
      ],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockSpeciesData,
    });

    const backendUrl = "http://localhost:8080";
    const result = await requestClassList({
      backendUrl,
      accessToken: "valid-token",
    });

    expect(result).toEqual(mockSpeciesData);
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "get",
      url: `${backendUrl}/seeds`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer valid-token`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: {},
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      requestClassList({ backendUrl: "", accessToken: "valid-token" }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });
});

describe("batchUploadInit", () => {
  it("should return session ID on success", async () => {
    const mockResponse = { sessionId: "session-123" };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const folderId = "folder-uuid";
    const nbPictures = 5;

    const result = await batchUploadInit({
      backendUrl,
      accessToken: "valid-token",
      folderId,
      fileCount: nbPictures,
    });

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "post",
      url: `${backendUrl}/new-batch-import`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer valid-token`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: {
        folderId: folderId,
        fileCount: nbPictures,
      },
      withCredentials: true,
    });
  });

  it("should throw ValueError for zero pictures", async () => {
    await expect(
      batchUploadInit({
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
        folderId: "folder-uuid",
        fileCount: 0,
      }),
    ).rejects.toThrow(new ValueError("Number of pictures is null or empty"));
  });

  it("should throw ValueError for empty folder ID", async () => {
    await expect(
      batchUploadInit({
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
        folderId: "",
        fileCount: 5,
      }),
    ).rejects.toThrow(new ValueError("Folder ID is null or empty"));
  });
});

describe("batchUploadImage", () => {
  const mockBatchUploadData = {
    sessionId: "session-456",
    seedId: "seed-uuid-123",
    trayCode: "A",
    sampleIdPrefix: "SAMPLE-123",
    deviceBrandId: "550e8400-e29b-41d4-a716-446655440000",
    deviceModelId: "550e8400-e29b-41d4-a716-446655440001",
    deviceLensId: "550e8400-e29b-41d4-a716-446655440002",
    magnification: 10.5,
    imageDataUrl: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ",
  };

  it("should upload image successfully", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: {
        pictureId: "picture-uuid-789",
        workflowId: "workflow-uuid-456",
      },
    });

    const backendUrl = "http://localhost:8080";
    const result = await batchUploadImage({
      backendUrl,
      data: mockBatchUploadData,
      accessToken: "valid-token",
    });

    expect(result.pictureId).toBe("picture-uuid-789");
    expect(result.workflowId).toBe("workflow-uuid-456");
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "post",
      url: `${backendUrl}/upload-picture`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer valid-token`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: {
        sessionId: mockBatchUploadData.sessionId,
        seedId: mockBatchUploadData.seedId,
        trayCode: mockBatchUploadData.trayCode,
        sampleId: mockBatchUploadData.sampleIdPrefix,
        deviceBrandId: mockBatchUploadData.deviceBrandId,
        deviceModelId: mockBatchUploadData.deviceModelId,
        deviceLensId: mockBatchUploadData.deviceLensId,
        magnification: mockBatchUploadData.magnification,
        image: mockBatchUploadData.imageDataUrl,
      },
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      batchUploadImage({
        backendUrl: "",
        data: mockBatchUploadData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty session ID", async () => {
    const invalidData = { ...mockBatchUploadData, sessionId: "" };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Session ID is null or empty"));
  });

  it("should throw ValueError for empty image data", async () => {
    const invalidData = { ...mockBatchUploadData, imageDataUrl: "" };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Image is null or empty"));
  });

  it("should throw ValueError for empty seed ID", async () => {
    const invalidData = { ...mockBatchUploadData, seedId: "" };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Seed ID is null or empty"));
  });

  it("should throw ValueError for zero magnification", async () => {
    const invalidData = { ...mockBatchUploadData, magnification: 0 };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Magnification is null or empty"));
  });

  it("should throw ValueError for empty tray code", async () => {
    const invalidData = { ...mockBatchUploadData, trayCode: "" };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Tray code is null or empty"));
  });

  it("should throw ValueError for empty sample ID prefix", async () => {
    const invalidData = { ...mockBatchUploadData, sampleIdPrefix: "" };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Sample ID Prefix is null or empty"));
  });

  it("should throw ValueError for empty device brand", async () => {
    const invalidData = { ...mockBatchUploadData, deviceBrandId: "" };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Device brand is null or empty"));
  });

  it("should throw ValueError for empty device model", async () => {
    const invalidData = { ...mockBatchUploadData, deviceModelId: "" };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Device model is null or empty"));
  });

  it("should throw ValueError for empty device lens", async () => {
    const invalidData = { ...mockBatchUploadData, deviceLensId: "" };
    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: invalidData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Device lens is null or empty"));
  });

  it("should handle upload errors", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "Upload failed - file too large",
        status: 413,
      },
    });

    await expect(
      batchUploadImage({
        backendUrl: "http://localhost:8080",
        data: mockBatchUploadData,
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new AzureAPIError("Upload failed - file too large"));
    console.error = consoleError;
  });
});

describe("sendPositiveFeedback", () => {
  const mockPositiveFeedbackData = {
    userId: "user-123",
    inferenceId: "inference-456",
    boxes: [{ boxId: "box-1" }, { boxId: "box-2" }],
  };

  it("should send positive feedback successfully", async () => {
    const mockResponse = {
      filename: "test.jpg",
      imageId: "img-123",
      inferenceId: "inf-456",
      boxes: [],
      labelOccurrence: { seed_name: 2 },
      totalBoxes: 2,
      models: [{ name: "test-model", version: "1" }],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const result = await sendPositiveFeedback({
      feedbackData: mockPositiveFeedbackData,
      backendUrl,
      accessToken: "valid-token",
    });

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "post",
      url: `${backendUrl}/feedback-positive`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer valid-token`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: mockPositiveFeedbackData,
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      sendPositiveFeedback({
        feedbackData: mockPositiveFeedbackData,
        backendUrl: "",
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should handle feedback processing errors", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "Inference not found",
        status: 404,
      },
    });

    await expect(
      sendPositiveFeedback({
        feedbackData: mockPositiveFeedbackData,
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new AzureAPIError("Inference not found"));
    console.error = consoleError;
  });
});

describe("sendNegativeFeedback", () => {
  const mockNegativeFeedbackData = {
    userId: "user-123",
    inferenceId: "inference-456",
    boxes: [
      {
        label: "incorrect-label",
        classId: "class-1",
        boxId: "box-1",
        box: { topX: 10, topY: 10, bottomX: 50, bottomY: 50 },
        comment: "This is not the correct classification",
        family: "Poaceae",
        genus: "Avena",
        species: "fatua",
        nameCode: "AVEFA",
      },
    ],
  };

  it("should send negative feedback successfully", async () => {
    const mockResponse = {
      filename: "test.jpg",
      imageId: "img-123",
      inferenceId: "inf-456",
      boxes: [],
      labelOccurrence: { seed_name: 0 },
      totalBoxes: 0,
      models: [{ name: "test-model", version: "1" }],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const result = await sendNegativeFeedback({
      feedbackData: mockNegativeFeedbackData,
      backendUrl,
      accessToken: "valid-token",
    });

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "post",
      url: `${backendUrl}/feedback-negative`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer valid-token`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: mockNegativeFeedbackData,
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      sendNegativeFeedback({
        feedbackData: mockNegativeFeedbackData,
        backendUrl: "",
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });
});

describe("sendFeedbackNewBox", () => {
  const mockNewBoxFeedbackData = {
    userId: "user-123",
    inferenceId: "inference-456",
    boxes: [
      {
        label: "new-seed-type",
        classId: "class-new",
        boxId: "box-new",
        box: { topX: 15, topY: 15, bottomX: 55, bottomY: 55 },
        comment: "Found an additional seed that was missed",
        family: "Brassicaceae",
        genus: "Sinapis",
        species: "arvensis",
        nameCode: "SINAR",
      },
    ],
  };

  it("should send new box feedback successfully", async () => {
    const mockResponse = {
      filename: "test.jpg",
      imageId: "img-123",
      inferenceId: "inf-456",
      boxes: [
        {
          topN: [{ score: 0.95, label: "new-seed-type" }],
          score: 0.95,
          label: "new-seed-type",
          classId: "class-new",
          objectTypeId: "obj-1",
          boxId: "box-new",
          box: { topX: 15, topY: 15, bottomX: 55, bottomY: 55 },
          overlapping: false,
          overlappingIndices: 0,
          isVerified: true,
        },
      ],
      labelOccurrence: { "new-seed-type": 1 },
      totalBoxes: 1,
      models: [{ name: "test-model", version: "1" }],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const result = await sendFeedbackNewBox({
      feedbackData: mockNewBoxFeedbackData,
      backendUrl,
      accessToken: "valid-token",
    });

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith({
      method: "post",
      url: `${backendUrl}/feedback-new-box`,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        Authorization: `Bearer valid-token`,
        "X-Correlation-ID": "test-correlation-id",
        "X-Session-ID": "test-session-id",
      },
      data: mockNewBoxFeedbackData,
      withCredentials: true,
    });
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      sendFeedbackNewBox({
        feedbackData: mockNewBoxFeedbackData,
        backendUrl: "",
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should handle validation errors for new boxes", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      response: {
        data: "Invalid box coordinates",
        status: 400,
      },
    });

    await expect(
      sendFeedbackNewBox({
        feedbackData: mockNewBoxFeedbackData,
        backendUrl: "http://localhost:8080",
        accessToken: "valid-token",
      }),
    ).rejects.toThrow(new AzureAPIError("Invalid box coordinates"));
    console.error = consoleError;
  });
});
