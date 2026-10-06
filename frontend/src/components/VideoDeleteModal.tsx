import React, { useState } from 'react';
import { deleteVideo } from '../api/video';
import type { LocalVideoMeta } from '../types/video';

interface VideoDeleteModalProps {
  video: LocalVideoMeta | null;
  onClose: () => void;
  onDeleted: (uuid: string) => Promise<void>;
}

const VideoDeleteModal: React.FC<VideoDeleteModalProps> = ({
  video,
  onClose,
  onDeleted,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const handleClose = () => {
    if (isDeleting) {
      return;
    }
    setDeleteError('');
    onClose();
  };

  const handleDelete = async () => {
    if (!video) {
      return;
    }

    setIsDeleting(true);
    setDeleteError('');
    try {
      await deleteVideo(video.uuid);
      await onDeleted(video.uuid);
      setDeleteError('');
      onClose();
    } catch (error) {
      const errorResponse = error as { message?: string };
      console.error('Failed to delete video:', error);
      setDeleteError(errorResponse.message || 'Failed to delete video. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  if (!video) {
    return null;
  }

  return (
    <div className="modal-overlay">
      <div className="modal-container" role="dialog" aria-modal="true" aria-labelledby="delete-video-title">
        <div className="modal-header">
          <div className="modal-title" id="delete-video-title">Delete Video</div>
          <button
            className="modal-close-btn"
            onClick={handleClose}
            disabled={isDeleting}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="modal-body">
          {deleteError && (
            <div className="alert alert-error" role="alert">
              <span>{deleteError}</span>
            </div>
          )}
          <p>
            Delete <strong>{video.title}</strong>? This will permanently remove the
            video and its search data.
          </p>
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="modal-cancel-btn"
            onClick={handleClose}
            disabled={isDeleting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="auth-button"
            style={{ marginTop: 0, padding: '8px 20px', fontSize: '14px' }}
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting ? 'Deleting...' : 'Delete Video'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoDeleteModal;
