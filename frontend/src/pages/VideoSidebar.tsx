import React, { useState } from 'react';
import VideoCard from '../components/VideoCard';
import VideoDeleteModal from '../components/VideoDeleteModal';
import VideoUploadModal from '../components/VideoUploadModal';
import type { LocalVideoMeta } from '../types/video';

interface VideoSidebarProps {
  videos: LocalVideoMeta[];
  setSessionFiles: React.Dispatch<React.SetStateAction<{ [uuid: string]: File }>>;
  selectedVideoUuid: string;
  onSelectVideo: (uuid: string) => void;
  refreshVideos: () => Promise<LocalVideoMeta[]>;
}

export const VideoSidebar: React.FC<VideoSidebarProps> = ({
  videos,
  setSessionFiles,
  selectedVideoUuid,
  onSelectVideo,
  refreshVideos,
}) => {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [videoPendingDelete, setVideoPendingDelete] = useState<LocalVideoMeta | null>(null);

  const handleVideoDeleted = async (uuid: string) => {
    if (selectedVideoUuid === uuid) {
      onSelectVideo('');
    }
    setSessionFiles((previous) => {
      const remainingFiles = { ...previous };
      delete remainingFiles[uuid];
      return remainingFiles;
    });
    await refreshVideos();
  };

  const handleUploaded = async (file: File, title: string) => {
    const updatedVideos = await refreshVideos();
    const newUploaded = updatedVideos.find((video) => video.title === title);
    if (newUploaded) {
      setSessionFiles((previous) => ({
        ...previous,
        [newUploaded.uuid]: file,
      }));
      onSelectVideo(newUploaded.uuid);
    }
  };

  return (
    <>
      <div className="sidebar-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '12px' }}>
          <div className="sidebar-title">Registered Videos</div>
        </div>
        <button className="upload-btn" onClick={() => setIsUploadModalOpen(true)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Register Video
        </button>
      </div>

      <div className="sidebar-content">
        {videos.length === 0 ? (
          <div className="video-list-empty">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ opacity: 0.5 }}>
              <path d="M15 10L19.5528 7.72361C20.2177 7.39116 21 7.87465 21 8.61803V15.382C21 16.1254 20.2177 16.6088 19.5528 16.2764L15 14M4 17H14C15.1046 17 16 16.1046 16 15V9C16 7.89543 15.1046 7 14 7H4C2.89543 7 2 7.89543 2 9V15C2 16.1046 2.89543 17 4 17Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>No videos registered yet. Click the button above to upload.</span>
          </div>
        ) : (
          videos.map((video) => (
            <VideoCard
              key={video.uuid}
              video={video}
              isSelected={selectedVideoUuid === video.uuid}
              onSelect={onSelectVideo}
              onDelete={() => setVideoPendingDelete(video)}
            />
          ))
        )}
      </div>

      <VideoUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploaded={handleUploaded}
      />
      <VideoDeleteModal
        video={videoPendingDelete}
        onClose={() => setVideoPendingDelete(null)}
        onDeleted={handleVideoDeleted}
      />
    </>
  );
};

export default VideoSidebar;
