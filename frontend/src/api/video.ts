import apiClient from './client';

export interface UploadVideoResponse {
  file_name: string;
  result: string;
}

export type VideoState = 'queued' | 'in_progress' | 'extracted' | 'complete' | 'aborted' | 'error';

export const TERMINAL_VIDEO_STATES: VideoState[] = ['complete', 'aborted', 'error'];

export interface VideoItem {
  uuid: string;
  title: string;
  state: VideoState;
  uploaded_time: string;
}

export interface FrameSearchResult {
  frame_id: number;
  timestamp: number;
  index: number;
  thumbnail_url: string | null;
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
 * Backend endpoint: GET /video/url/{uuid}
 */
export const getVideoUrl = async (uuid: string): Promise<VideoUrlResponse> => {
  const response = await apiClient.get<VideoUrlResponse>(`/video/url/${uuid}`);
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
 * Streams the frames matching a text query from the CLIP search endpoint.
 * The server sends a "result" event with the frames, or an "error" event.
 * Backend endpoint: GET /clip/query/{video_uuid}?query_text=...
 */
export const queryClip = async (queryText: string, videoUuid: string): Promise<FrameSearchResult[]> => {
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
  let frames: FrameSearchResult[] | null = null;
  let errorMessage: string | null = null;

  const readEvent = (event: string) => {
    const lines = event.split(/\r?\n/);
    const eventType = lines
      .find((line) => line.startsWith('event:'))
      ?.slice(6)
      .trim() || 'message';
    const data = lines
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n');
    if (!data) return;

    const parsed: unknown = JSON.parse(data);
    if (eventType === 'error') {
      errorMessage = (parsed as { detail?: string })?.detail || 'Search failed.';
    } else if (Array.isArray(parsed)) {
      frames = parsed as FrameSearchResult[];
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

  if (errorMessage) {
    throw new Error(errorMessage);
  }
  if (!frames) {
    throw new Error('The CLIP query completed without returning frames.');
  }
  return frames;
};

/**
 * Subscribes to the processing state of a video until it reaches a terminal state.
 * Returns a function that closes the stream.
 * Backend endpoint: GET /video/progress/{uuid} (SSE)
 */
export const watchVideoProgress = (
  uuid: string,
  onState: (state: VideoState) => void,
): (() => void) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const url = new URL(`/video/progress/${encodeURIComponent(uuid)}`, baseUrl);
  const source = new EventSource(url, { withCredentials: true });

  source.onmessage = (event) => {
    const state = JSON.parse(event.data) as VideoState;
    onState(state);
    // EventSource reconnects automatically, so close it once processing is over
    if (TERMINAL_VIDEO_STATES.includes(state)) {
      source.close();
    }
  };
  source.onerror = () => source.close();

  return () => source.close();
};

/**
 * Deletes a video.
 * Backend endpoint: DELETE /video/{uuid}
 */
export const deleteVideo = async (uuid: string): Promise<{ result: string }> => {
  const response = await apiClient.delete<{ result: string }>(`/video/${uuid}`);
  return response.data;
};



