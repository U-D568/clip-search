import React, { useRef, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { uploadVideo } from '../api/video';

interface LocalVideoMeta {
  uuid: string;
  title: string;
  state: 'queued' | 'in_progress' | 'complete' | 'f_complete' | 'error';
  uploaded_time: string;
  fileName: string;
}

interface VideoSidebarProps {
  videos: LocalVideoMeta[];
  setVideos: React.Dispatch<React.SetStateAction<LocalVideoMeta[]>>;
  setSessionFiles: React.Dispatch<React.SetStateAction<{ [uuid: string]: File }>>;
  selectedVideoUuid: string;
  onSelectVideo: (uuid: string) => void;
}

export const VideoSidebar: React.FC<VideoSidebarProps> = ({
  videos,
  setVideos,
  setSessionFiles,
  selectedVideoUuid,
  onSelectVideo,
}) => {
  const { getCurrentUser } = useAuth();
  const user = getCurrentUser();

  // Local Modal States
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  const saveVideos = (updatedVideos: LocalVideoMeta[]) => {
    if (user) {
      localStorage.setItem(`videos_${user.username}`, JSON.stringify(updatedVideos));
      setVideos(updatedVideos);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a video file.');
      return;
    }
    if (!uploadTitle.trim()) {
      setUploadError('Please enter a title for the video.');
      return;
    }

    setIsUploading(true);
    setUploadError('');

    try {
      const localUuid = crypto.randomUUID();
      await uploadVideo(uploadFile, uploadTitle);

      const newVideo: LocalVideoMeta = {
        uuid: localUuid,
        title: uploadTitle,
        state: 'queued' as const,
        uploaded_time: new Date().toISOString(),
        fileName: uploadFile.name
      };

      setSessionFiles(prev => ({
        ...prev,
        [localUuid]: uploadFile
      }));

      saveVideos([newVideo, ...videos]);
      onSelectVideo(localUuid);
      
      setUploadFile(null);
      setUploadTitle('');
      setIsUploadModalOpen(false);

      // Simulate status updates (Mocks)
      setTimeout(() => {
        setVideos(current => {
          const updated = current.map(v => v.uuid === localUuid ? { ...v, state: 'in_progress' as const } : v);
          localStorage.setItem(`videos_${user?.username}`, JSON.stringify(updated));
          return updated;
        });
      }, 5000);

      setTimeout(() => {
        setVideos(current => {
          const updated = current.map(v => v.uuid === localUuid ? { ...v, state: 'complete' as const } : v);
          localStorage.setItem(`videos_${user?.username}`, JSON.stringify(updated));
          return updated;
        });
      }, 15000);

    } catch (err) {
      const errorResponse = err as { message: string };
      console.error(err);
      setUploadError(errorResponse.message || 'Failed to upload video.');
    } finally {
      setIsUploading(false);
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
          videos.map((vid) => (
            <div
              key={vid.uuid}
              className={`video-card ${selectedVideoUuid === vid.uuid ? 'active' : ''}`}
              onClick={() => onSelectVideo(vid.uuid)}
            >
              <div className="video-card-title">{vid.title}</div>
              <div className="video-card-meta">
                <span>{new Date(vid.uploaded_time).toLocaleDateString()}</span>
                <span className={`status-badge ${vid.state}`}>
                  {vid.state === 'f_complete' ? 'complete' : vid.state.replace('_', ' ')}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Upload/Register Video Modal */}
      {isUploadModalOpen && (
        <div className="modal-overlay">
          <div className="modal-container">
            <div className="modal-header">
              <div className="modal-title">Register New Video</div>
              <button className="modal-close-btn" onClick={() => setIsUploadModalOpen(false)}>×</button>
            </div>
            
            <form onSubmit={handleUploadSubmit}>
              <div className="modal-body">
                {uploadError && (
                  <div className="alert alert-error">
                    <svg className="alert-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                      <path d="M12 8V12M12 16H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                    <span>{uploadError}</span>
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Video Title</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    style={{ paddingLeft: '14px' }}
                    placeholder="Enter a friendly title for your video"
                    value={uploadTitle}
                    onChange={(e) => setUploadTitle(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Video File (.mp4)</label>
                  <div 
                    className="drag-drop-zone"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <div className="drag-drop-icon">📁</div>
                    <div className="drag-drop-text">
                      {uploadFile ? (
                        <strong>Selected: {uploadFile.name} ({Math.round(uploadFile.size / 1024 / 1024)}MB)</strong>
                      ) : (
                        'Click to browse or drop an MP4 video file here'
                      )}
                    </div>
                  </div>
                  <input 
                    ref={fileInputRef}
                    type="file" 
                    accept="video/mp4" 
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        setUploadFile(file);
                        if (!uploadTitle) {
                          const baseName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
                          setUploadTitle(baseName);
                        }
                      }
                    }}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button 
                  type="button" 
                  className="modal-cancel-btn" 
                  onClick={() => setIsUploadModalOpen(false)}
                  disabled={isUploading}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="auth-button"
                  style={{ marginTop: 0, padding: '8px 20px', fontSize: '14px' }}
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <>
                      <div className="spinner"></div>
                      Uploading...
                    </>
                  ) : (
                    'Upload & Register'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default VideoSidebar;
