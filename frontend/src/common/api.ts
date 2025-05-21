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
} from "./types";

const handleAxios = async <T>(request: {
  method: string;
  url: string;
  headers: { [label: string]: string };
  data: any;
}): Promise<T> => {
  const data = await axios(request)
    .then((response) => {
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
        console.error(error.response.headers);
        throw new AzureAPIError(error.response.data);
      } else if (error.request) {
        console.error(error.request);
        throw new AzureAPIError(error.request);
      } else {
        console.error("Error", error.message);
      }
      console.error(error.config);
      throw new AzureAPIError(error.config);
    });
  return data;
};

export const readAzureStorageDir = async (
  backendUrl: string,
  uuid: string,
): Promise<ReadAzureStorageDirApi> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (uuid === "" || uuid == null) {
    throw new ValueError("UUID is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/get-directories`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: {
      container_name: uuid,
    },
  };
  return handleAxios(request);
};

export const createAzureStorageDir = async (
  backendUrl: string,
  uuid: string,
  folderName: string,
): Promise<void> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (uuid === "" || uuid == null) {
    throw new ValueError("UUID is null or empty");
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
    },
    data: {
      container_name: uuid,
      folder_name: folderName,
    },
  };
  return handleAxios(request);
};

export const deleteAzureStorageDir = async (
  backendUrl: string,
  uuid: string,
  folderName: string,
): Promise<void> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (uuid === "" || uuid == null) {
    throw new ValueError("UUID is null or empty");
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
    },
    data: {
      container_name: uuid,
      folder_name: folderName,
    },
  };
  return handleAxios(request);
};

export const inferenceRequest = async (
  backendUrl: string,
  selectedModel: string,
  imageObject: Images,
  curDir: string,
  uuid: string,
  container_uuid: string,
): Promise<ApiInferenceData> => {
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
  if (uuid === "" || uuid == null) {
    throw new ValueError("UUID is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/inf`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: {
      model_name: selectedModel,
      image: imageObject.src,
      imageDims: imageObject.imageDims,
      folder_name: curDir,
      user_id: uuid,
      container_name: container_uuid,
    },
  };
  return handleAxios<ApiInferenceData>(request);
};

export const fetchModelMetadata = async (
  backendUrl: string,
): Promise<ModelMetadata[]> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const request = {
    method: "get",
    url: `${backendUrl}/model-endpoints-metadata`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: {},
  };
  return handleAxios<ModelMetadata[]>(request);
};

export const sendFeedbackNewBox = async (
  feedbackData: FeedbackDataNegative,
  backendUrl: string,
): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/feedback-new-box`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: feedbackData,
  };
  return handleAxios<ApiInferenceData>(request);
};

export const sendPositiveFeedback = async (
  feedbackData: FeedbackDataPositive,
  backendUrl: string,
): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/feedback-positive`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: feedbackData,
  };
  return handleAxios<ApiInferenceData>(request);
};

export const sendNegativeFeedback = async (
  feedbackData: FeedbackDataNegative,
  backendUrl: string,
): Promise<ApiInferenceData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/feedback-negative`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: feedbackData,
  };
  return handleAxios<ApiInferenceData>(request);
};

export const requestUUID = async (
  backendUrl: string,
  email: string,
): Promise<{
  user_id: string;
}> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/get-user-id`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: {
      email: email,
    },
    withCredentials: true,
  };
  return handleAxios<{
    user_id: string;
  }>(request);
};

export const requestClassList = async (
  backendUrl: string,
  // uuid: string,
): Promise<ApiSpeciesData> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  // if (uuid === "" || uuid == null) {
  //   throw new ValueError("UUID is null or empty");
  // }
  const request = {
    method: "get",
    url: `${backendUrl}/seeds`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: {},
    // data: {
    //   uuid: uuid,
    // },
  };
  return handleAxios<ApiSpeciesData>(request);
};

export const batchUploadInit = async (
  backendUrl: string,
  uuid: string,
  folderName: string,
  containerUuid: string,
  nbPictures: number,
): Promise<{
  session_id: string;
}> => {
  if (backendUrl === "" || backendUrl == null) {
    throw new ValueError("Backend URL is null or empty");
  }
  if (uuid === "" || uuid == null) {
    throw new ValueError("UUID is null or empty");
  }
  if (containerUuid === "" || containerUuid == null) {
    throw new ValueError("Container UUID is null or empty");
  }
  if (nbPictures === 0 || nbPictures == null) {
    throw new ValueError("Number of pictures is null or empty");
  }
  const request = {
    method: "post",
    url: `${backendUrl}/new-batch-import`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    data: {
      user_id: uuid,
      folder_name: folderName,
      container_name: containerUuid,
      nb_pictures: nbPictures,
    },
  };
  return handleAxios<{
    session_id: string;
  }>(request);
};

export const batchUploadImage = async (
  backendUrl: string,
  data: BatchUploadMetadata,
): Promise<boolean> => {
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
  const request = {
    method: "post",
    url: `${backendUrl}/upload-picture`,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
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
  return handleAxios(request);
};
