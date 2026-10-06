import React from 'react';
import type { LocalVideoMeta } from '../types/video';

interface VideoCardProps {
  video: LocalVideoMeta;
  isSelected: boolean;
  onSelect: (uuid: string) => void;
  onDelete: (uuid: string) => void;
}

const VideoCard: React.FC<VideoCardProps> = ({
  video,
  isSelected,
  onSelect,
  onDelete,
}) => (
  <div
    className={`video-card ${isSelected ? 'active' : ''}`}
    onClick={() => onSelect(video.uuid)}
  >
    <div className="video-card-header">
      <div className="video-card-title">{video.title}</div>
      <button
        className="delete-video-btn"
        onClick={(event) => {
          event.stopPropagation();
          onDelete(video.uuid);
        }}
        title="Delete video"
        aria-label={`Delete ${video.title}`}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          <line x1="10" y1="11" x2="10" y2="17"></line>
          <line x1="14" y1="11" x2="14" y2="17"></line>
        </svg>
      </button>
    </div>
    <div className="video-card-meta">
      <span>{new Date(video.uploaded_time).toLocaleDateString()}</span>
      <span className={`status-badge ${video.state}`}>{video.state}</span>
    </div>
  </div>
);

export default VideoCard;
