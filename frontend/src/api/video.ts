import apiClient from './client';

export interface UploadVideoResponse {
  file_name: string;
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
 * Streams matching frame IDs from the CLIP search endpoint.
 * Backend endpoint: GET /clip/query/{video_uuid}?query_text=...
 */
export const queryClip = async (queryText: string, videoUuid: string): Promise<string[]> => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const url = new URL(`/clip/query/${encodeURIComponent(videoUuid)}`, baseUrl);
  url.searchParams.set('query_text', queryText);

  const response = await fetch(url, {
    headers: { Accept: 'text/event-stream' },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail || `CLIP query failed (${response.status})`);
  }
  if (!response.body) {
    throw new Error('The CLIP query response did not include a stream.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let frameIds: string[] | null = null;

  const readEvent = (event: string) => {
    const data = event
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n');
    if (!data) return;

    const parsed: unknown = JSON.parse(data);
    if (Array.isArray(parsed)) {
      frameIds = parsed.map(String);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() || '';
    events.forEach(readEvent);

    if (done) {
      if (buffer.trim()) readEvent(buffer);
      break;
    }
  }

  if (!frameIds) {
    throw new Error('The CLIP query completed without returning frame IDs.');
  }
  return frameIds;
};

/**
 * Deletes a video.
 * Backend endpoint: DELETE /video/{uuid}
 */
export const deleteVideo = async (uuid: string): Promise<{ result: string }> => {
  const response = await apiClient.delete<{ result: string }>(`/video/${uuid}`);
  return response.data;
};



