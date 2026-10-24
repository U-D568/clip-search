import React, { useRef, useState } from 'react';
import { uploadVideo } from '../api/video';

interface VideoUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploaded: (file: File, title: string) => Promise<void>;
}

const VideoUploadModal: React.FC<VideoUploadModalProps> = ({
  isOpen,
  onClose,
  onUploaded,
}) => {
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClose = () => {
    setUploadTitle('');
    setUploadFile(null);
    setIsUploading(false);
    setUploadError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onClose();
  };

  const handleUploadSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
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
      const title = uploadTitle;
      const file = uploadFile;
      await uploadVideo(file, title);

      handleClose();

      await onUploaded(file, title);
    } catch (err) {
      const errorResponse = err as { message?: string };
      console.error(err);
      setUploadError(errorResponse.message || 'Failed to upload video.');
    } finally {
      setIsUploading(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay">
      <div className="modal-container">
        <div className="modal-header">
          <div className="modal-title">Register New Video</div>
          <button className="modal-close-btn" onClick={handleClose} disabled={isUploading}>×</button>
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
                value={uploadTitle}
                onChange={(event) => setUploadTitle(event.target.value)}
                disabled={isUploading}
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
                    <strong>
                      Selected: {uploadFile.name} ({Math.round(uploadFile.size / 1024 / 1024)}MB)
                    </strong>
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
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    setUploadFile(file);
                  }
                }}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="modal-cancel-btn"
              onClick={handleClose}
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
  );
};

export default VideoUploadModal;
