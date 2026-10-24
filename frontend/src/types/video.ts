import type { VideoState } from '../api/video';

export interface LocalVideoMeta {
  uuid: string;
  title: string;
  state: VideoState;
  uploaded_time: string;
  fileName: string;
}
