import axios from "axios";
import { AzureAPIError, ValueError } from "./error";
import {
  ApiInferenceData,
  ApiSpeciesData,
  BatchUploadMetadata,
  BatchUploadImageResponse,
  CreateOrGetFolderResponse,
  UpdateFolderResponse,
  FeedbackDataNegative,
  FeedbackDataPositive,
  Images,
  ModelMetadata,
  ReadAzureStorageDirApi,
  ApiDevicesResponse,
} from "./types";
import { z } from "zod";
import {
  validateApiResponse,
  // UserIdResponseSchema,
  BooleanResponseSchema,
  IsRegisteredResponseSchema,
  // VoidResponseSchema,
  ReadAzureStorageDirApiSchema,
  ApiInferenceDataSchema,
  ModelMetadataSchema,
  ApiSpeciesDataSchema,
  ApiDevicesResponseSchema,
  ImageSubmissionResponseSchema,
  WorkflowStatusResponseSchema,
  InferenceRequestSchema,
  ImageSubmissionResponse,
  WorkflowStatusResponse,
  BatchUploadImageResponseSchema,
  BatchUploadInitResponseSchema,
  CreateOrGetFolderResponseSchema,
  UpdateFolderResponseSchema,
  normalizedPathSchema,
  safeUserInputSchema,
} from "./validation";
import { errorLogger } from "../logging";
import { setupAxiosInterceptor, resetRedirectFlag } from "./apiInterceptor";
import type { IPublicClientApplication } from "@azure/msal-browser";

/**
 * Initialize API module with axios interceptor for authentication
 * Must be called once during app initialization
 *
 * @param msalInstance - MSAL instance for authentication
 * @param scopes - Array of scopes to request for tokens
 */
export function initializeApi(
  msalInstance: IPublicClientApplication,
  scopes: string[],
): void {
  setupAxiosInterceptor(msalInstance, scopes);
}

// Re-export resetRedirectFlag for use in main.tsx
export { resetRedirectFlag };

const handleAxios = async <T>(request: {
  method: string;
  url: string;
  headers: { [label: string]: string };
  data?: any;
}): Promise<T> => {
  // Generate correlation ID for this request
  const correlationId = errorLogger.getCorrelationId();

  // Add correlation and session IDs to headers
  const enhancedRequest = {
    ...request,
    headers: {
      ...request.headers,
      "X-Correlation-ID": correlationId,
      "X-Session-ID": errorLogger.getSessionId(),
    },
    withCredentials: true,
  };

  const data = await axios(enhancedRequest)
    .then((response) => {
      // Extract correlation ID from response if available
      const responseCorrelationId = response.headers?.["x-correlation-id"];
      if (responseCorrelationId) {
        errorLogger.setCorrelationId(responseCorrelationId);
      }
      if (response.status === 200) {
        return response.data;
      } else {
        throw new AzureAPIError(response.data);
      }
    })
    .catch((error) => {
      if (error.response) {
        console.error(error.response.data);
        console.error(error.response.status);
        console.error(error.response.headers); // Log API error with details
        errorLogger.logApiError(
          request.url,
          error.response?.status || 0,
          error.response?.statusText || "Unknown",
          error.response?.data || "No response data",
          error.response?.headers?.["x-correlation-id"] || correlationId,
        );

        // Extract error message from response data
        let errorMessage = "API Error";
        const responseData = error.response?.data;
        if (responseData) {
          if (typeof responseData === "string") {
            errorMessage = responseData;
          } else if (responseData.detail) {
            errorMessage = responseData.detail;
          } else if (responseData.message) {
            errorMessage = responseData.message;
          } else {
            errorMessage = JSON.stringify(responseData);
          }
        }
        throw new AzureAPIError(errorMessage);
      } else if (error.request) {
        console.error(error.request); // Log network error
        errorLogger.logError(
          `Network error: No response received from ${request.url}`,
          new Error("Network request failed"),
          { request: error.request, correlationId },
        );
        throw new AzureAPIError("Network request failed");
      } else {
        console.error("Error", error.message); // Log other errors
        errorLogger.logError(
          `Request setup error: ${error.message || "Unknown error"}`,
          error,
          {
            config: error.config,
            correlationId,
          },
        );
      }

      console.error(error.config);

      throw new AzureAPIError(error.message || "Unknown error");
    });
  return data;
};

export const pingBackend = async ({
  backendUrl,
}: {
  backendUrl: string;
}): Promise<boolean> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/health`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  };
  const response = await handleAxios<{ status: string }>(request);
  return validateApiResponse(
    BooleanResponseSchema,
    response.status == "ok",
    "pingBackend",
  );
};

export const checkUserRegistration = async ({
  backendUrl,
  accessToken,
}: {
  backendUrl: string;
  accessToken: string;
}): Promise<{ is_registered: boolean }> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/is-registered`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    IsRegisteredResponseSchema,
    response,
    "checkUserRegistration",
  );
};

export const readAzureStorageDir = async ({
  backendUrl,
  accessToken,
}: {
  backendUrl: string;
  accessToken: string;
}): Promise<ReadAzureStorageDirApi> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/get-directories`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    // data: {
    //   //   container_name: uuid,
    // },
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ReadAzureStorageDirApiSchema,
    response,
    "readAzureStorageDir",
  );
};

export const createAzureStorageDir = async ({
  backendUrl,
  accessToken,
  folderName,
}: {
  backendUrl: string;
  accessToken: string;
  folderName: string;
}): Promise<boolean> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  if (folderName === "" || folderName == null) {
    throw new ValueError("Folder name is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/create-dir`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      folder_name: folderName,
    },
  };
  const response = await handleAxios<{ folder_name: string }>(request);
  return validateApiResponse(
    BooleanResponseSchema,
    response.folder_name === folderName,
    "createAzureStorageDir",
  );
};

/**
 * Delete a folder (soft delete).
 * @deprecated Use deleteFolder instead - this function uses old endpoint
 */
export const deleteAzureStorageDir = async ({
  backendUrl,
  accessToken,
  folderName,
}: {
  backendUrl: string;
  accessToken: string;
  folderName: string;
}): Promise<boolean> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  if (folderName === "" || folderName == null) {
    throw new ValueError("Folder name is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/del`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      folder_name: folderName,
    },
  };
  const response = await handleAxios<{ folder_name: string }>(request);
  return validateApiResponse(
    BooleanResponseSchema,
    response.folder_name === folderName,
    "deleteAzureStorageDir",
  );
};

/**
 * Delete a folder by ID using the new DELETE /folders/{folder_id} endpoint.
 */
export const deleteFolder = async ({
  backendUrl,
  accessToken,
  folderId,
}: {
  backendUrl: string;
  accessToken: string;
  folderId: string;
}): Promise<{ id: string; message: string }> => {
  if (!backendUrl) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (!accessToken) {
    throw new ValueError("Access token is null or empty");
  }
  if (!folderId) {
    throw new ValueError("Folder ID is null or empty");
  }

  const request = {
    method: "delete",
    url: `${backendUrl}/folders/${folderId}`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
  };

  const response = await handleAxios<unknown>(request);

  // Define response schema
  const DeleteFolderResponseSchema = z.object({
    id: z.string().uuid(),
    message: z.string(),
  });

  return validateApiResponse(
    DeleteFolderResponseSchema,
    response,
    "deleteFolder",
  );
};

export const inferenceRequest = async ({
  backendUrl,
  selectedModel,
  imageObject,
  curDir,
  accessToken,
  folder_id,
}: {
  backendUrl: string;
  selectedModel: string;
  imageObject: Images;
  curDir: string;
  accessToken: string;
  folder_id: string;
}): Promise<ImageSubmissionResponse> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (selectedModel === "" || selectedModel == null) {
    throw new ValueError("Model is null or empty");
  }
  if (imageObject.src === "" || imageObject.src == null) {
    throw new ValueError("Image is null or empty");
  }
  if (curDir === "" || curDir == null) {
    throw new ValueError("Directory is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }

  // Build payload object with all required and optional fields
  const payload = {
    pipelineId: selectedModel,
    folderName: curDir,
    folderId: folder_id,
    imageDims: imageObject.imageDims,
    image: imageObject.src,
    // Include device and sample metadata if available
    ...(imageObject.deviceBrandId && {
      deviceBrandId: imageObject.deviceBrandId,
    }),
    ...(imageObject.deviceModelId && {
      deviceModelId: imageObject.deviceModelId,
    }),
    ...(imageObject.deviceLensId && {
      deviceLensId: imageObject.deviceLensId,
    }),
    ...(imageObject.trayCode && { trayCode: imageObject.trayCode }),
    ...(imageObject.magnification && {
      magnification: imageObject.magnification,
    }),
    // Include image identification fields
    ...(imageObject.imageName && { imageName: imageObject.imageName }),
    ...(imageObject.imageDescription && {
      imageDescription: imageObject.imageDescription,
    }),
  };

  // Validate payload against schema
  const validatedPayload = InferenceRequestSchema.parse(payload);

  const request = {
    method: "post",
    url: `${backendUrl}/inf`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: validatedPayload,
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ImageSubmissionResponseSchema,
    response,
    "inferenceRequest",
  );
};

export const inferenceDirectRequest = async ({
  backendUrl,
  selectedModel,
  imageObject,
  curDir,
  accessToken,
  folder_id,
}: {
  backendUrl: string;
  selectedModel: string;
  imageObject: Images;
  curDir: string;
  accessToken: string;
  folder_id: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (selectedModel === "" || selectedModel == null) {
    throw new ValueError("Model is null or empty");
  }
  if (imageObject.src === "" || imageObject.src == null) {
    throw new ValueError("Image is null or empty");
  }
  if (curDir === "" || curDir == null) {
    throw new ValueError("Directory is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }

  // Build payload object with all required and optional fields
  const payload = {
    pipelineId: selectedModel,
    folderName: curDir,
    folderId: folder_id,
    imageDims: imageObject.imageDims,
    image: imageObject.src,
    // Include device and sample metadata if available
    ...(imageObject.deviceBrandId && {
      deviceBrandId: imageObject.deviceBrandId,
    }),
    ...(imageObject.deviceModelId && {
      deviceModelId: imageObject.deviceModelId,
    }),
    ...(imageObject.deviceLensId && {
      deviceLensId: imageObject.deviceLensId,
    }),
    ...(imageObject.trayCode && { trayCode: imageObject.trayCode }),
    ...(imageObject.magnification && {
      magnification: imageObject.magnification,
    }),
    // Include image identification fields
    ...(imageObject.imageName && { imageName: imageObject.imageName }),
    ...(imageObject.imageDescription && {
      imageDescription: imageObject.imageDescription,
    }),
  };

  // Validate payload against schema
  const validatedPayload = InferenceRequestSchema.parse(payload);

  const request = {
    method: "post",
    url: `${backendUrl}/inf-direct`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: validatedPayload,
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ApiInferenceDataSchema,
    response,
    "inferenceRequest",
  );
};

export const fetchModelMetadata = async ({
  backendUrl,
  accessToken,
}: {
  backendUrl: string;
  accessToken: string;
}): Promise<ModelMetadata[]> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/model-endpoints-metadata`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {},
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    z.array(ModelMetadataSchema),
    response,
    "fetchModelMetadata",
  );
};

export const fetchDevices = async ({
  backendUrl,
  accessToken,
}: {
  backendUrl: string;
  accessToken: string;
}): Promise<ApiDevicesResponse> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/devices`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {},
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ApiDevicesResponseSchema,
    response,
    "fetchDevices",
  );
};

export const getWorkflowStatus = async ({
  backendUrl,
  workflowId,
  accessToken,
}: {
  backendUrl: string;
  workflowId: string;
  accessToken: string;
}): Promise<WorkflowStatusResponse> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (workflowId === "" || workflowId == null) {
    throw new ValueError("Workflow ID is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/workflow/${workflowId}/status`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {},
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    WorkflowStatusResponseSchema,
    response,
    "getWorkflowStatus",
  );
};

export const getWorkflowResults = async ({
  backendUrl,
  workflowId,
  accessToken,
}: {
  backendUrl: string;
  workflowId: string;
  accessToken: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (workflowId === "" || workflowId == null) {
    throw new ValueError("Workflow ID is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/workflow/${workflowId}/results`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {},
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ApiInferenceDataSchema,
    response,
    "getWorkflowResults",
  );
};

export const sendFeedbackNewBox = async ({
  feedbackData,
  backendUrl,
  accessToken,
}: {
  feedbackData: FeedbackDataNegative;
  backendUrl: string;
  accessToken: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/feedback-new-box`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: feedbackData,
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ApiInferenceDataSchema,
    response,
    "sendFeedbackNewBox",
  );
};

export const sendPositiveFeedback = async ({
  feedbackData,
  backendUrl,
  accessToken,
}: {
  feedbackData: FeedbackDataPositive;
  backendUrl: string;
  accessToken: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/feedback-positive`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: feedbackData,
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ApiInferenceDataSchema,
    response,
    "sendPositiveFeedback",
  );
};

export const sendNegativeFeedback = async ({
  feedbackData,
  backendUrl,
  accessToken,
}: {
  feedbackData: FeedbackDataNegative;
  backendUrl: string;
  accessToken: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/feedback-negative`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: feedbackData,
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ApiInferenceDataSchema,
    response,
    "sendNegativeFeedback",
  );
};

// export const requestUUID = async (
//   backendUrl: string,
//   email: string,
// ): Promise<{
//   user_id: string;
// }> => {
//   if (backendUrl === "" || backendUrl == null) {
//     throw new ValueError("Backend URL is null or empty");
//   }
//   const request = {
//     method: "post",
//     url: `${backendUrl}/get-user-id`,
//     headers: {
//       "Content-Type": "application/json",
//       "Access-Control-Allow-Origin": "*",
//     },
//     data: {
//       email: email,
//     },
//     withCredentials: true,
//   };
//   const response = await handleAxios<unknown>(request);
//   return validateApiResponse(UserIdResponseSchema, response, "requestUUID");
// };

export const requestClassList = async ({
  backendUrl,
  accessToken,
}: {
  backendUrl: string;
  accessToken: string;
}): Promise<ApiSpeciesData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/seeds`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {},
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    ApiSpeciesDataSchema,
    response,
    "requestClassList",
  );
};

export const batchUploadInit = async ({
  backendUrl,
  accessToken,
  folderId,
  fileCount,
}: {
  backendUrl: string;
  accessToken: string;
  folderId: string;
  fileCount: number;
}): Promise<{
  session_id: string;
}> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  if (folderId === "" || folderId == null) {
    throw new ValueError("Folder ID is null or empty");
  }
  if (fileCount === 0 || fileCount == null) {
    throw new ValueError("Number of pictures is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/new-batch-import`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      folder_id: folderId,
      file_count: fileCount,
    },
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    BatchUploadInitResponseSchema,
    response,
    "batchUploadInit",
  );
};

export const batchUploadImage = async ({
  backendUrl,
  data,
  accessToken,
}: {
  backendUrl: string;
  data: BatchUploadMetadata;
  accessToken: string;
}): Promise<BatchUploadImageResponse> => {
  const {
    sessionId,
    seedId,
    trayCode,
    sampleIdPrefix,
    deviceBrandId,
    deviceModelId,
    deviceLensId,
    magnification,
    imageDataUrl,
  } = data;

  // Validation
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (sessionId === "" || sessionId == null) {
    throw new ValueError("Session ID is null or empty");
  }
  if (seedId === "" || seedId == null) {
    throw new ValueError("Seed ID is null or empty");
  }
  if (imageDataUrl === "" || imageDataUrl == null) {
    throw new ValueError("Image is null or empty");
  }
  if (trayCode === "" || trayCode == null) {
    throw new ValueError("Tray code is null or empty");
  }
  if (sampleIdPrefix === "" || sampleIdPrefix == null) {
    throw new ValueError("Sample ID Prefix is null or empty");
  }
  if (deviceBrandId === "" || deviceBrandId == null) {
    throw new ValueError("Device brand is null or empty");
  }
  if (deviceModelId === "" || deviceModelId == null) {
    throw new ValueError("Device model is null or empty");
  }
  if (deviceLensId === "" || deviceLensId == null) {
    throw new ValueError("Device lens is null or empty");
  }
  if (magnification === 0 || magnification == null) {
    throw new ValueError("Magnification is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }

  const request = {
    method: "post",
    url: `${backendUrl}/upload-picture`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      session_id: sessionId,
      seed_id: seedId,
      tray_code: trayCode,
      sample_id: sampleIdPrefix,
      device_brand_id: deviceBrandId,
      device_model_id: deviceModelId,
      device_lens_id: deviceLensId,
      magnification: magnification,
      image: imageDataUrl,
    },
  };

  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    BatchUploadImageResponseSchema,
    response,
    "batchUploadImage",
  );
};

/**
 * Create or get a folder using the get-or-create pattern (idempotent).
 *
 * This function sends a normalized path to the backend. If the folder exists,
 * it returns the existing folder_id. If not, it creates a new folder and
 * returns the new folder_id.
 *
 * @param backendUrl - Backend API base URL
 * @param accessToken - JWT access token for authentication
 * @param normalizedPath - Relative path (e.g., "avena-fatua" or "mycology/avena-fatua")
 * @param description - Optional description for the folder (defaults to empty string)
 * @returns Promise resolving to CreateOrGetFolderResponse with folder_id
 * @throws ValueError if parameters are invalid
 * @throws AzureAPIError if API request fails
 *
 * @example
 * const result = await createOrGetFolder({
 *   backendUrl: "http://localhost:8080",
 *   accessToken: "eyJhbGc...",
 *   normalizedPath: "avena-fatua",
 *   description: "Wild oat samples"
 * });
 * // Returns: { folder_id: "uuid-string" }
 */
export const createOrGetFolder = async ({
  backendUrl,
  accessToken,
  normalizedPath,
  description = "",
}: {
  backendUrl: string;
  accessToken: string;
  normalizedPath: string;
  description?: string;
}): Promise<CreateOrGetFolderResponse> => {
  // Validation
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  if (normalizedPath === "" || normalizedPath == null) {
    throw new ValueError("Normalized path is null or empty");
  }

  // Validate path format using Zod schema
  const pathValidation = normalizedPathSchema.safeParse(normalizedPath);
  if (!pathValidation.success) {
    throw new ValueError(
      `Invalid normalized path: ${pathValidation.error.issues[0].message}`,
    );
  }

  const request = {
    method: "post",
    url: `${backendUrl}/folders`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      normalized_path: normalizedPath,
      description: description,
    },
  };

  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    CreateOrGetFolderResponseSchema,
    response,
    "createOrGetFolder",
  );
};

/**
 * Update Folder API
 *
 * Updates a folder's name and/or description.
 *
 * Authorization: Users with folder's org_user_role_id OR org_admin_role_id OR CFIA admin
 * Restrictions: Cannot update default folders for active users
 *
 * @param backendUrl - Backend API base URL
 * @param accessToken - Bearer token for authentication
 * @param folderId - UUID of the folder to update
 * @param name - Optional new folder name (just the name, not full path)
 * @param description - Optional new description
 * @returns Promise resolving to UpdateFolderResponse
 * @throws ValueError if parameters are invalid
 * @throws AxiosError if API call fails
 *
 * @example
 * await updateFolder({
 *   backendUrl: "https://api.example.com",
 *   accessToken: "bearer-token",
 *   folderId: "uuid-string",
 *   name: "new-folder-name",
 *   description: "Updated description"
 * });
 * // Returns: { id: "uuid-string", message: "Folder updated successfully" }
 */
export const updateFolder = async ({
  backendUrl,
  accessToken,
  folderId,
  name,
  description,
}: {
  backendUrl: string;
  accessToken: string;
  folderId: string;
  name?: string;
  description?: string;
}): Promise<UpdateFolderResponse> => {
  // Validation
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  if (folderId === "" || folderId == null) {
    throw new ValueError("Folder ID is null or empty");
  }
  if (!name && !description) {
    throw new ValueError(
      "At least one field (name or description) must be provided",
    );
  }

  // Validate name if provided
  if (name) {
    const nameValidation = normalizedPathSchema.safeParse(name);
    if (!nameValidation.success) {
      throw new ValueError(
        `Invalid folder name: ${nameValidation.error.issues[0].message}`,
      );
    }
  }

  // Sanitize description if provided
  if (description) {
    const descriptionValidation = safeUserInputSchema.safeParse(description);
    if (!descriptionValidation.success) {
      throw new ValueError(
        `Invalid description: ${descriptionValidation.error.issues[0].message}`,
      );
    }
  }

  const request = {
    method: "put",
    url: `${backendUrl}/folders/${folderId}`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      ...(name && { name }),
      ...(description && { description }),
    },
  };

  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    UpdateFolderResponseSchema,
    response,
    "updateFolder",
  );
};

export const sendLogToBackend = async ({
  backendUrl,
  accessToken,
  logData,
}: {
  backendUrl: string;
  accessToken: string;
  logData: {
    level: "ERROR" | "WARNING" | "INFO" | "DEBUG";
    message: string;
    error_type?: string;
    stack_trace?: string;
    url?: string;
    timestamp?: string;
    user_agent?: string;
    extra?: Record<string, any>;
  };
}): Promise<void> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (accessToken === "" || accessToken == null) {
    throw new ValueError("Access token is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/logs`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: logData,
  };
  await handleAxios<unknown>(request);
};
