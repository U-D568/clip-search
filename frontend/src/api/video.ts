import apiClient from './client';

export interface UploadVideoResponse {
  file_name: string;
  result: string;
}

export interface QueryVideoResponse {
  task_id: string;
  result: string;
}

export interface QueryResultResponse {
  timestamps: string[];
  result: string;
}

export interface VideoItem {
  uuid: string;
  title: string;
  state: 'queued' | 'processing' | 'complete' | 'error';
  uploaded_time: string;
}

export interface VideoUrlResponse {
  url: string;
}

/**
 * Fetches all registered videos for the logged-in user.
 * Backend endpoint: GET /video/list
 */
export const getVideos = async (): Promise<VideoItem[]> => {
  const response = await apiClient.get<VideoItem[]>('/video/list');
  return response.data;
};

/**
 * Fetches the S3 presigned URL for playing a video.
 * Backend endpoint: GET /video/{uuid}/url
 */
export const getVideoUrl = async (uuid: string): Promise<VideoUrlResponse> => {
  const response = await apiClient.get<VideoUrlResponse>(`/video/${uuid}/url`);
  return response.data;
};

/**
 * Uploads a video file to the backend.
 * Backend endpoint: POST /video/upload
 */
export const uploadVideo = async (file: File, title: string): Promise<UploadVideoResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);
  
  const response = await apiClient.post<UploadVideoResponse>('/video/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Initiates a search query on a specific video.
 * Backend endpoint: POST /video/query
 */
export const queryVideo = async (queryText: string, videoUuid: string): Promise<QueryVideoResponse> => {
  const formData = new FormData();
  formData.append('query_text', queryText);
  formData.append('video_uuid', videoUuid);

  const response = await apiClient.post<QueryVideoResponse>('/video/query', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Deletes a video.
 * Backend endpoint: DELETE /video/{uuid}
 */
export const deleteVideo = async (uuid: string): Promise<{ result: string }> => {
  const response = await apiClient.delete<{ result: string }>(`/video/${uuid}`);
  return response.data;
};



