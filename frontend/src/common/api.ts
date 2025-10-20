import axios from "axios";
import { AzureAPIError, ValueError } from "./error";
import {
  ApiInferenceData,
  ApiSpeciesData,
  BatchUploadMetadata,
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
  SessionIdResponseSchema,
  BooleanResponseSchema,
  IsRegisteredResponseSchema,
  // VoidResponseSchema,
  ReadAzureStorageDirApiSchema,
  ApiInferenceDataSchema,
  ModelMetadataSchema,
  ApiSpeciesDataSchema,
  ApiDevicesResponseSchema,
} from "./validation";
import { errorLogger } from "../logging";

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
        throw new AzureAPIError(error.response?.data || "API Error");
      } else if (error.request) {
        console.error(error.request); // Log network error
        errorLogger.logError(
          `Network error: No response received from ${request.url}`,
          new Error("Network request failed"),
          { request: error.request, correlationId },
        );
        throw new AzureAPIError(error.request);
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

      throw new AzureAPIError(error.config || error.message);
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

export const inferenceRequest = async ({
  backendUrl,
  selectedModel,
  imageObject,
  curDir,
  accessToken,
  container_uuid,
}: {
  backendUrl: string;
  selectedModel: string;
  imageObject: Images;
  curDir: string;
  accessToken: string;
  container_uuid: string;
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
  const request = {
    method: "post",
    url: `${backendUrl}/inf`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      model_name: selectedModel,
      image: imageObject.src,
      imageDims: imageObject.imageDims,
      folder_name: curDir,
      container_name: container_uuid,
    },
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
  folderName,
  containerUuid,
  fileCount,
}: {
  backendUrl: string;
  accessToken: string;
  folderName: string;
  containerUuid: string;
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
  if (containerUuid === "" || containerUuid == null) {
    throw new ValueError("Container UUID is null or empty");
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
      folder_name: folderName,
      container_name: containerUuid,
      file_count: fileCount,
    },
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    SessionIdResponseSchema,
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
}): Promise<boolean> => {
  const {
    containerName,
    uuid,
    seedId,
    seedName, // TODO: remove when backend is implemented
    zoom,
    seedCount,
    sessionId,
    imageDataUrl,
  } = data;
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (sessionId === "" || sessionId == null) {
    throw new ValueError("Session ID is null or empty");
  }
  if (imageDataUrl === "" || imageDataUrl == null) {
    throw new ValueError("Image is null or empty");
  }
  if (containerName === "" || containerName == null) {
    throw new ValueError("Container name is null or empty");
  }
  if (uuid === "" || uuid == null) {
    throw new ValueError("UUID is null or empty");
  }
  if (seedId === "" || seedId == null) {
    throw new ValueError("Seed ID is null or empty");
  }
  if (zoom === 0 || zoom == null) {
    throw new ValueError("Zoom is null or empty");
  }
  if (seedCount === 0 || seedCount == null) {
    throw new ValueError("Seed count is null or empty");
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
      container_name: containerName,
      user_id: uuid,
      seed_id: seedId,
      seed_name: seedName, // TODO: remove when backend is implemented
      zoom_level: zoom,
      nb_seeds: seedCount,
      session_id: sessionId,
      image: imageDataUrl,
    },
  };
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    BooleanResponseSchema,
    response,
    "batchUploadImage",
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
