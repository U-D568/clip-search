export interface LocalVideoMeta {
  uuid: string;
  title: string;
  state: 'queued' | 'processing' | 'complete' | 'error';
  uploaded_time: string;
  fileName: string;
}
