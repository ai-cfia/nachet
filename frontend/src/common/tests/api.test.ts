import { describe, it, vi, beforeEach, expect } from "vitest";
import {
  createAzureStorageDir,
  deleteAzureStorageDir,
  fetchModelMetadata,
  inferenceRequest,
  readAzureStorageDir,
  sendPositiveFeedback,
  sendNegativeFeedback,
  sendFeedbackNewBox,
  requestUUID,
  requestClassList,
  batchUploadInit,
  batchUploadImage,
} from "../api";
import axios from "axios";
import { AzureAPIError, ValueError } from "../error";

// mock axios
vi.mock("axios");
const mockedAxios = vi.mocked(axios);

beforeEach(() => {
  mockedAxios.mockClear();
});

describe("readAzureStorageDir", () => {
  it("should return data on success", async () => {
    const mockData = {
      folders: [
        {
          folder_name: "test-folder",
          nb_pictures: 5,
          picture_set_id: "set-123",
          pictures: [],
        },
      ],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockData,
    });
    const backendUrl = "http://localhost:8080";
    const uuid = "valid-uuid";

    const result = await readAzureStorageDir(backendUrl, uuid);
    expect(result).toEqual(mockData);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/get-directories`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {
        container_name: uuid,
      },
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(readAzureStorageDir("", "valid-uuid")).rejects.toThrow(
      new ValueError("Backend URL is null or empty"),
    );
  });

  it("should throw ValueError for null backend URL", async () => {
    await expect(
      readAzureStorageDir(null as any, "valid-uuid"),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty UUID", async () => {
    await expect(
      readAzureStorageDir("http://localhost:8080", ""),
    ).rejects.toThrow(new ValueError("UUID is null or empty"));
  });

  it("should throw ValueError for null UUID", async () => {
    await expect(
      readAzureStorageDir("http://localhost:8080", null as any),
    ).rejects.toThrow(new ValueError("UUID is null or empty"));
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
    // Note: console.error is not called for response errors in the enhanced error handling
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

  it("should handle generic error with message", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    mockedAxios.mockRejectedValue({
      message: "Network error",
      config: "error config",
    });
    const backendUrl = "http://localhost:8080";
    const uuid = "valid-uuid";

    await expect(readAzureStorageDir(backendUrl, uuid)).rejects.toEqual(
      new AzureAPIError("error config"),
    );
    // Updated expectation to match the enhanced error logging format
    expect(console.error).toHaveBeenCalledWith(
      "Request setup error: Network error",
      expect.objectContaining({ message: "Network error" }),
      expect.objectContaining({ config: "error config" })
    );
    console.error = consoleError;
  });

  it("should handle non-200 status codes", async () => {
    mockedAxios.mockResolvedValue({
      status: 201,
      data: "created",
    });
    const backendUrl = "http://localhost:8080";
    const uuid = "valid-uuid";

    await expect(readAzureStorageDir(backendUrl, uuid)).rejects.toThrow(
      AzureAPIError,
    );
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
  it("should create directory successfully", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: undefined,
    });
    const backendUrl = "http://localhost:8080";
    const uuid = "valid-uuid";
    const folderName = "test-folder";

    await createAzureStorageDir(backendUrl, uuid, folderName);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/create-dir`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {
        container_name: uuid,
        folder_name: folderName,
      },
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      createAzureStorageDir("", "valid-uuid", "folder"),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty UUID", async () => {
    await expect(
      createAzureStorageDir("http://localhost:8080", "", "folder"),
    ).rejects.toThrow(new ValueError("UUID is null or empty"));
  });

  it("should throw ValueError for empty folder name", async () => {
    await expect(
      createAzureStorageDir("http://localhost:8080", "valid-uuid", ""),
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
      createAzureStorageDir("http://localhost:8080", "valid-uuid", "folder"),
    ).rejects.toThrow(new AzureAPIError("Permission denied"));
    console.error = consoleError;
  });
});

describe("deleteAzureStorageDir", () => {
  it("should delete directory successfully", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: undefined,
    });
    const backendUrl = "http://localhost:8080";
    const uuid = "valid-uuid";
    const folderName = "test-folder";

    await deleteAzureStorageDir(backendUrl, uuid, folderName);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/del`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {
        container_name: uuid,
        folder_name: folderName,
      },
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      deleteAzureStorageDir("", "valid-uuid", "folder"),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty UUID", async () => {
    await expect(
      deleteAzureStorageDir("http://localhost:8080", "", "folder"),
    ).rejects.toThrow(new ValueError("UUID is null or empty"));
  });

  it("should throw ValueError for empty folder name", async () => {
    await expect(
      deleteAzureStorageDir("http://localhost:8080", "valid-uuid", ""),
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
      deleteAzureStorageDir(
        "http://localhost:8080",
        "valid-uuid",
        "nonexistent",
      ),
    ).rejects.toThrow(new AzureAPIError("Directory not found"));
    console.error = consoleError;
  });
});

describe("inferenceRequest", () => {
  const mockImageObject = {
    index: 0,
    src: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ",
    scores: [],
    classifications: [],
    boxes: [],
    annotated: false,
    imageDims: [640, 480],
    overlapping: [],
    overlappingIndices: [],
    topN: [],
  };

  it("should return inference data on success", async () => {
    const mockInferenceData = {
      filename: "test.jpg",
      imageId: "img-123",
      inference_id: "inf-456",
      boxes: [],
      labelOccurrence: { seed_name: 0 },
      totalBoxes: 0,
      models: [{ name: "test-model", version: 1 }],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockInferenceData,
    });

    const backendUrl = "http://localhost:8080";
    const uuid = "user-uuid";
    const containerUuid = "container-uuid";
    const curDir = "test-directory";
    const selectedModel = "swin-transformer";

    const result = await inferenceRequest(
      backendUrl,
      selectedModel,
      mockImageObject,
      curDir,
      uuid,
      containerUuid,
    );

    expect(result).toEqual(mockInferenceData);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/inf`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {
        model_name: selectedModel,
        image: mockImageObject.src,
        imageDims: mockImageObject.imageDims,
        folder_name: curDir,
        user_id: uuid,
        container_name: containerUuid,
      },
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      inferenceRequest(
        "",
        "model",
        mockImageObject,
        "dir",
        "uuid",
        "container",
      ),
    ).rejects.toThrow(new ValueError("Backend URL is null or empty"));
  });

  it("should throw ValueError for empty model", async () => {
    await expect(
      inferenceRequest(
        "http://localhost:8080",
        "",
        mockImageObject,
        "dir",
        "uuid",
        "container",
      ),
    ).rejects.toThrow(new ValueError("Model is null or empty"));
  });

  it("should throw ValueError for empty image", async () => {
    const emptyImageObject = { ...mockImageObject, src: "" };
    await expect(
      inferenceRequest(
        "http://localhost:8080",
        "model",
        emptyImageObject,
        "dir",
        "uuid",
        "container",
      ),
    ).rejects.toThrow(new ValueError("Image is null or empty"));
  });

  it("should throw ValueError for empty directory", async () => {
    await expect(
      inferenceRequest(
        "http://localhost:8080",
        "model",
        mockImageObject,
        "",
        "uuid",
        "container",
      ),
    ).rejects.toThrow(new ValueError("Directory is null or empty"));
  });

  it("should throw ValueError for empty UUID", async () => {
    await expect(
      inferenceRequest(
        "http://localhost:8080",
        "model",
        mockImageObject,
        "dir",
        "",
        "container",
      ),
    ).rejects.toThrow(new ValueError("UUID is null or empty"));
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
      inferenceRequest(
        "http://localhost:8080",
        "invalid-model",
        mockImageObject,
        "dir",
        "uuid",
        "container",
      ),
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
      inferenceRequest(
        "http://localhost:8080",
        "model",
        mockImageObject,
        "dir",
        "uuid",
        "container",
      ),
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
      inferenceRequest(
        "http://localhost:8080",
        "model",
        mockImageObject,
        "dir",
        "uuid",
        "container",
      ),
    ).rejects.toThrow(new AzureAPIError("Network timeout"));
    console.error = consoleError;
  });
});

describe("handleAxios error scenarios", () => {
  it("should handle non-200 status in successful response", async () => {
    mockedAxios.mockResolvedValue({
      status: 202,
      data: "accepted",
    });

    await expect(fetchModelMetadata("http://localhost:8080")).rejects.toThrow(
      AzureAPIError,
    );
  });
});

describe("fetchModelMetadata", () => {
  it("should return model metadata on success", async () => {
    const mockMetadata = [
      {
        created_by: "test-user",
        creation_date: "2023-12-01",
        dataset: "seed-dataset-v1",
        description: "Test model for seed detection",
        identifiable: ["wheat", "oat", "barley"],
        job_name: "test_job_123",
        metrics: ["precision: 0.95", "recall: 0.92"],
        model_name: "Seed Detector v1",
        models: ["detector-model-123"],
        pipeline_name: "seed-detection-pipeline",
        default: true,
      },
    ];
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockMetadata,
    });

    const backendUrl = "http://localhost:8080";
    const result = await fetchModelMetadata(backendUrl);

    expect(result).toEqual(mockMetadata);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "get",
      url: `${backendUrl}/model-endpoints-metadata`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {},
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(fetchModelMetadata("")).rejects.toThrow(
      new ValueError("Backend URL is null or empty"),
    );
  });

  it("should throw ValueError for null backend URL", async () => {
    await expect(fetchModelMetadata(null as any)).rejects.toThrow(
      new ValueError("Backend URL is null or empty"),
    );
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

    await expect(fetchModelMetadata("http://localhost:8080")).rejects.toThrow(
      new AzureAPIError("Service temporarily unavailable"),
    );
    console.error = consoleError;
  });

  it("should handle empty metadata response", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: [],
    });

    const result = await fetchModelMetadata("http://localhost:8080");
    expect(result).toEqual([]);
  });
});

describe("requestUUID", () => {
  it("should return user ID on success", async () => {
    const mockResponse = { user_id: "user-123" };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const email = "test@example.com";
    const result = await requestUUID(backendUrl, email);

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/get-user-id`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {
        email: email,
      },
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(requestUUID("", "test@example.com")).rejects.toThrow(
      new ValueError("Backend URL is null or empty"),
    );
  });
});

describe("requestClassList", () => {
  it("should return species data on success", async () => {
    const mockSpeciesData = {
      seeds: [
        { seed_id: "1", seed_name: "Wheat" },
        { seed_id: "2", seed_name: "Oat" },
      ],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockSpeciesData,
    });

    const backendUrl = "http://localhost:8080";
    const result = await requestClassList(backendUrl);

    expect(result).toEqual(mockSpeciesData);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "get",
      url: `${backendUrl}/seeds`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {},
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(requestClassList("")).rejects.toThrow(
      new ValueError("Backend URL is null or empty"),
    );
  });
});

describe("batchUploadInit", () => {
  it("should return session ID on success", async () => {
    const mockResponse = { session_id: "session-123" };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const uuid = "user-uuid";
    const folderName = "test-folder";
    const containerUuid = "container-uuid";
    const nbPictures = 5;

    const result = await batchUploadInit(
      backendUrl,
      uuid,
      folderName,
      containerUuid,
      nbPictures,
    );

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/new-batch-import`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {
        user_id: uuid,
        folder_name: folderName,
        container_name: containerUuid,
        nb_pictures: nbPictures,
      },
      withCredentials: true,
    }));
  });

  it("should throw ValueError for zero pictures", async () => {
    await expect(
      batchUploadInit(
        "http://localhost:8080",
        "uuid",
        "folder",
        "container",
        0,
      ),
    ).rejects.toThrow(new ValueError("Number of pictures is null or empty"));
  });

  it("should throw ValueError for empty container UUID", async () => {
    await expect(
      batchUploadInit("http://localhost:8080", "uuid", "folder", "", 5),
    ).rejects.toThrow(new ValueError("Container UUID is null or empty"));
  });
});

describe("batchUploadImage", () => {
  const mockBatchUploadData = {
    containerName: "test-container",
    uuid: "user-uuid",
    seedId: "seed-123",
    seedName: "Test Seed",
    zoom: 10,
    seedCount: 5,
    imageDataUrl: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ",
    sessionId: "session-456",
  };

  it("should upload image successfully", async () => {
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: true,
    });

    const backendUrl = "http://localhost:8080";
    const result = await batchUploadImage(backendUrl, mockBatchUploadData);

    expect(result).toBe(true);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/upload-picture`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: {
        container_name: mockBatchUploadData.containerName,
        user_id: mockBatchUploadData.uuid,
        seed_id: mockBatchUploadData.seedId,
        seed_name: mockBatchUploadData.seedName,
        zoom_level: mockBatchUploadData.zoom,
        nb_seeds: mockBatchUploadData.seedCount,
        session_id: mockBatchUploadData.sessionId,
        image: mockBatchUploadData.imageDataUrl,
      },
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(batchUploadImage("", mockBatchUploadData)).rejects.toThrow(
      new ValueError("Backend URL is null or empty"),
    );
  });

  it("should throw ValueError for empty session ID", async () => {
    const invalidData = { ...mockBatchUploadData, sessionId: "" };
    await expect(
      batchUploadImage("http://localhost:8080", invalidData),
    ).rejects.toThrow(new ValueError("Session ID is null or empty"));
  });

  it("should throw ValueError for empty image data", async () => {
    const invalidData = { ...mockBatchUploadData, imageDataUrl: "" };
    await expect(
      batchUploadImage("http://localhost:8080", invalidData),
    ).rejects.toThrow(new ValueError("Image is null or empty"));
  });

  it("should throw ValueError for empty container name", async () => {
    const invalidData = { ...mockBatchUploadData, containerName: "" };
    await expect(
      batchUploadImage("http://localhost:8080", invalidData),
    ).rejects.toThrow(new ValueError("Container name is null or empty"));
  });

  it("should throw ValueError for empty UUID", async () => {
    const invalidData = { ...mockBatchUploadData, uuid: "" };
    await expect(
      batchUploadImage("http://localhost:8080", invalidData),
    ).rejects.toThrow(new ValueError("UUID is null or empty"));
  });

  it("should throw ValueError for empty seed ID", async () => {
    const invalidData = { ...mockBatchUploadData, seedId: "" };
    await expect(
      batchUploadImage("http://localhost:8080", invalidData),
    ).rejects.toThrow(new ValueError("Seed ID is null or empty"));
  });

  it("should throw ValueError for zero zoom", async () => {
    const invalidData = { ...mockBatchUploadData, zoom: 0 };
    await expect(
      batchUploadImage("http://localhost:8080", invalidData),
    ).rejects.toThrow(new ValueError("Zoom is null or empty"));
  });

  it("should throw ValueError for zero seed count", async () => {
    const invalidData = { ...mockBatchUploadData, seedCount: 0 };
    await expect(
      batchUploadImage("http://localhost:8080", invalidData),
    ).rejects.toThrow(new ValueError("Seed count is null or empty"));
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
      batchUploadImage("http://localhost:8080", mockBatchUploadData),
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
      inference_id: "inf-456",
      boxes: [],
      labelOccurrence: { seed_name: 2 },
      totalBoxes: 2,
      models: [{ name: "test-model", version: 1 }],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const result = await sendPositiveFeedback(
      mockPositiveFeedbackData,
      backendUrl,
    );

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/feedback-positive`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: mockPositiveFeedbackData,
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      sendPositiveFeedback(mockPositiveFeedbackData, ""),
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
      sendPositiveFeedback(mockPositiveFeedbackData, "http://localhost:8080"),
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
      },
    ],
  };

  it("should send negative feedback successfully", async () => {
    const mockResponse = {
      filename: "test.jpg",
      imageId: "img-123",
      inference_id: "inf-456",
      boxes: [],
      labelOccurrence: { seed_name: 0 },
      totalBoxes: 0,
      models: [{ name: "test-model", version: 1 }],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const result = await sendNegativeFeedback(
      mockNegativeFeedbackData,
      backendUrl,
    );

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/feedback-negative`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: mockNegativeFeedbackData,
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      sendNegativeFeedback(mockNegativeFeedbackData, ""),
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
      },
    ],
  };

  it("should send new box feedback successfully", async () => {
    const mockResponse = {
      filename: "test.jpg",
      imageId: "img-123",
      inference_id: "inf-456",
      boxes: [
        {
          topN: [{ score: 0.95, label: "new-seed-type" }],
          score: 0.95,
          label: "new-seed-type",
          classId: "class-new",
          object_type_id: "obj-1",
          box_id: "box-new",
          box: { topX: 15, topY: 15, bottomX: 55, bottomY: 55 },
          overlapping: false,
          overlappingIndices: 0,
          is_verified: true,
        },
      ],
      labelOccurrence: { "new-seed-type": 1 },
      totalBoxes: 1,
      models: [{ name: "test-model", version: 1 }],
    };
    mockedAxios.mockResolvedValue({
      ok: true,
      status: 200,
      data: mockResponse,
    });

    const backendUrl = "http://localhost:8080";
    const result = await sendFeedbackNewBox(mockNewBoxFeedbackData, backendUrl);

    expect(result).toEqual(mockResponse);
    expect(mockedAxios).toHaveBeenCalledWith(expect.objectContaining({
      method: "post",
      url: `${backendUrl}/feedback-new-box`,
      headers: expect.objectContaining({
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }),
      data: mockNewBoxFeedbackData,
      withCredentials: true,
    }));
  });

  it("should throw ValueError for empty backend URL", async () => {
    await expect(
      sendFeedbackNewBox(mockNewBoxFeedbackData, ""),
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
      sendFeedbackNewBox(mockNewBoxFeedbackData, "http://localhost:8080"),
    ).rejects.toThrow(new AzureAPIError("Invalid box coordinates"));
    console.error = consoleError;
  });
});
