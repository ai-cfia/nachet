import axios, { AxiosHeaders } from "axios";
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
import {
  setupAxiosInterceptor,
  clearAxiosInterceptors,
  hasApiAccessTokenProvider,
} from "./apiInterceptor";
import type { NachetAuthTokenOptions } from "../auth/NachetAuthContext";

type GetApiAccessToken = (options?: NachetAuthTokenOptions) => Promise<string>;

/**
 * Initialize API module with axios interceptor for authentication
 * Must be called once during app initialization
 *
 * @param getApiAccessToken - Provider-neutral token getter used per request
 */
export const initializeApi = (getApiAccessToken: GetApiAccessToken): void => {
  setupAxiosInterceptor(getApiAccessToken);
};

export const clearApiAuthentication = (): void => {
  clearAxiosInterceptors();
};

const handleAxios = async <T>(request: {
  method: string;
  url: string;
  headers: Record<string, string>;
  data?: any;
  authRequired?: boolean;
}): Promise<T> => {
  // Generate correlation ID for this request
  const correlationId = errorLogger.getCorrelationId();
  const requestHasExplicitAuthHeader = hasAuthorizationHeader(request.headers);
  const requestRequiresAuth = request.authRequired ?? true;
  const requestCanUseAuthProvider =
    requestRequiresAuth && hasApiAccessTokenProvider();

  if (
    requestRequiresAuth &&
    !requestHasExplicitAuthHeader &&
    !requestCanUseAuthProvider
  ) {
    throw new ValueError("Auth provider is not initialized for API requests");
  }

  // Add correlation and session IDs to headers
  const enhancedRequest = {
    ...request,
    headers: {
      ...request.headers,
      "X-Correlation-ID": correlationId,
      "X-Session-ID": errorLogger.getSessionId(),
    },
    withCredentials: true,
    useNachetAuthProvider: requestCanUseAuthProvider,
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

// API helpers build plain header objects before Axios normalizes header names.
const hasAuthorizationHeader = (headers: Record<string, string>): boolean => {
  const authorizationHeader = AxiosHeaders.from(headers).get("Authorization");

  return (
    typeof authorizationHeader === "string" && authorizationHeader.trim() !== ""
  );
};

// During the API auth migration, callers either pass an explicit token
// or omit it so the Axios auth bridge can attach one.
const getAuthHeaders = (accessToken?: string): Record<string, string> => {
  if (accessToken === "") {
    throw new ValueError("Access token is empty");
  }

  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
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
    authRequired: false,
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
  accessToken?: string;
}): Promise<{ isRegistered: boolean }> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "get",
    url: `${backendUrl}/is-registered`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
}): Promise<ReadAzureStorageDirApi> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "get",
    url: `${backendUrl}/get-directories`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
  folderName: string;
}): Promise<boolean> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (folderName === "" || folderName == null) {
    throw new ValueError("Folder name is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/create-dir`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
    },
    data: {
      folderName: folderName,
    },
  };
  const response = await handleAxios<{ folderName: string }>(request);
  return validateApiResponse(
    BooleanResponseSchema,
    response.folderName === folderName,
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
  accessToken?: string;
  folderName: string;
}): Promise<boolean> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (folderName === "" || folderName == null) {
    throw new ValueError("Folder name is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/del`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
    },
    data: {
      folderName: folderName,
    },
  };
  const response = await handleAxios<{ folderName: string }>(request);
  return validateApiResponse(
    BooleanResponseSchema,
    response.folderName === folderName,
    "deleteAzureStorageDir",
  );
};

/**
 * Delete a folder by ID using the new DELETE /folders/{folderId} endpoint.
 */
export const deleteFolder = async ({
  backendUrl,
  accessToken,
  folderId,
}: {
  backendUrl: string;
  accessToken?: string;
  folderId: string;
}): Promise<{ id: string; message: string }> => {
  if (!backendUrl) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (!folderId) {
    throw new ValueError("Folder ID is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "delete",
    url: `${backendUrl}/folders/${folderId}`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  folderId,
}: {
  backendUrl: string;
  selectedModel: string;
  imageObject: Images;
  curDir: string;
  accessToken?: string;
  folderId: string;
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
  const authHeaders = getAuthHeaders(accessToken);

  // Build payload object with all required and optional fields
  const payload = {
    pipelineId: selectedModel,
    folderName: curDir,
    folderId: folderId,
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
      ...authHeaders,
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
  folderId,
}: {
  backendUrl: string;
  selectedModel: string;
  imageObject: Images;
  curDir: string;
  accessToken?: string;
  folderId: string;
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
  const authHeaders = getAuthHeaders(accessToken);

  // Build payload object with all required and optional fields
  const payload = {
    pipelineId: selectedModel,
    folderName: curDir,
    folderId: folderId,
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
      ...authHeaders,
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
  accessToken?: string;
}): Promise<ModelMetadata[]> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "get",
    url: `${backendUrl}/model-endpoints-metadata`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
}): Promise<ApiDevicesResponse> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "get",
    url: `${backendUrl}/devices`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
}): Promise<WorkflowStatusResponse> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (workflowId === "" || workflowId == null) {
    throw new ValueError("Workflow ID is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "get",
    url: `${backendUrl}/workflow/${workflowId}/status`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (workflowId === "" || workflowId == null) {
    throw new ValueError("Workflow ID is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "get",
    url: `${backendUrl}/workflow/${workflowId}/results`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/feedback-new-box`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/feedback-positive`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
}): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/feedback-negative`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
}): Promise<ApiSpeciesData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "get",
    url: `${backendUrl}/seeds`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
  folderId: string;
  fileCount: number;
}): Promise<{
  sessionId: string;
}> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (folderId === "" || folderId == null) {
    throw new ValueError("Folder ID is null or empty");
  }
  if (fileCount === 0 || fileCount == null) {
    throw new ValueError("Number of pictures is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/new-batch-import`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
    },
    data: {
      folderId: folderId,
      fileCount: fileCount,
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
  accessToken?: string;
}): Promise<BatchUploadImageResponse> => {
  const {
    sessionId,
    seedId,
    trayCode,
    sampleIdPrefix,
    sampleDescription,
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
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/upload-picture`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
    },
    data: {
      sessionId: sessionId,
      seedId: seedId,
      trayCode: trayCode,
      sampleId: sampleIdPrefix,
      deviceBrandId: deviceBrandId,
      deviceModelId: deviceModelId,
      deviceLensId: deviceLensId,
      magnification: magnification,
      image: imageDataUrl,
      ...(sampleDescription && { imageDescription: sampleDescription }),
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
 * Create or Get Folder API
 *
 * Creates a new folder or returns the existing one if a folder with the same
 * normalized path already exists for the user. If a folder with the same path exists,
 * it returns the existing folderId. If not, it creates a new folder and
 * returns the new folderId.
 *
 * Authorization: Users can only create folders for themselves
 *
 * @param backendUrl - Backend API base URL
 * @param accessToken - Optional compatibility bearer token. App callers normally use the shared auth provider.
 * @param normalizedPath - Relative path from user's root (e.g., "avena-fatua" or "mycology/avena-fatua")
 * @param description - Optional folder description
 * @returns Promise resolving to CreateOrGetFolderResponse with folderId
 * @throws ValueError if parameters are invalid
 * @throws AxiosError if API call fails
 *
 * @example
 * await createOrGetFolder({
 *   backendUrl: "https://api.example.com",
 *   normalizedPath: "mycology/avena-fatua",
 *   description: "Wild oat samples"
 * });
 * // Returns: { folderId: "uuid-string" }
 */
export const createOrGetFolder = async ({
  backendUrl,
  accessToken,
  normalizedPath,
  description = "",
}: {
  backendUrl: string;
  accessToken?: string;
  normalizedPath: string;
  description?: string;
}): Promise<CreateOrGetFolderResponse> => {
  // Validation
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
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
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/folders`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
    },
    data: {
      normalizedPath: normalizedPath,
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
 * Authorization: Users with folder's orgUserRoleId OR orgAdminRoleId OR CFIA admin
 * Restrictions: Cannot update default folders for active users
 *
 * @param backendUrl - Backend API base URL
 * @param accessToken - Optional compatibility bearer token. App callers normally use the shared auth provider.
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
  accessToken?: string;
  folderId: string;
  name?: string;
  description?: string;
}): Promise<UpdateFolderResponse> => {
  // Validation
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
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
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "put",
    url: `${backendUrl}/folders/${folderId}`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
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
  accessToken?: string;
  logData: {
    level: "ERROR" | "WARNING" | "INFO" | "DEBUG";
    message: string;
    errorType?: string;
    stackTrace?: string;
    url?: string;
    timestamp?: string;
    userAgent?: string;
    extra?: Record<string, any>;
  };
}): Promise<void> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const authHeaders = getAuthHeaders(accessToken);

  const request = {
    method: "post",
    url: `${backendUrl}/logs`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...authHeaders,
    },
    data: logData,
  };
  await handleAxios<unknown>(request);
};
