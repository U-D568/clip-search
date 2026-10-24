import React, { useEffect, useRef, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { getVideoUrl, queryClip } from '../api/video';
import type { FrameSearchResult } from '../api/video';
import type { DashboardContextType } from '../layouts/Dashboard';

export const Video: React.FC = () => {
  const {
    videos,
    sessionFiles,
    setSessionFiles,
    selectedVideoUuid,
  } = useOutletContext<DashboardContextType>();

  const [prompt, setPrompt] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchStatus, setSearchStatus] = useState('');
  const [searchResults, setSearchResults] = useState<FrameSearchResult[]>([]);
  const [searchError, setSearchError] = useState('');
  const [videoSource, setVideoSource] = useState<{ uuid: string; url: string } | null>(null);
  const [videoLoadError, setVideoLoadError] = useState<{ uuid: string; message: string } | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const relinkInputRef = useRef<HTMLInputElement>(null);
  const selectedVideo = videos.find((video) => video.uuid === selectedVideoUuid);
  const videoFile = selectedVideo ? sessionFiles[selectedVideo.uuid] : null;
  const videoSrc = videoSource?.uuid === selectedVideoUuid ? videoSource.url : '';
  const videoError = !videoFile && videoLoadError?.uuid === selectedVideoUuid
    ? videoLoadError.message
    : '';

  useEffect(() => {
    let isCurrent = true;

    if (!selectedVideo) return;
    if (videoFile) {
      const localUrl = URL.createObjectURL(videoFile);
      queueMicrotask(() => {
        if (isCurrent) setVideoSource({ uuid: selectedVideo.uuid, url: localUrl });
      });
      return () => {
        isCurrent = false;
        URL.revokeObjectURL(localUrl);
      };
    }

    getVideoUrl(selectedVideo.uuid)
      .then(({ url }) => {
        if (isCurrent) setVideoSource({ uuid: selectedVideo.uuid, url });
      })
      .catch((error: { message?: string }) => {
        if (isCurrent) {
          setVideoLoadError({
            uuid: selectedVideo.uuid,
            message: error.message || 'Could not load this video.',
          });
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedVideo, videoFile]);

  const handleRelinkFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && selectedVideoUuid) {
      setSessionFiles((previous) => ({
        ...previous,
        [selectedVideoUuid]: file,
      }));
    }
  };

  const handleSearchSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!prompt.trim() || !selectedVideoUuid) return;

    setIsSearching(true);
    setSearchError('');
    setSearchResults([]);
    setSearchStatus('Searching video frames...');

    try {
      const frames = await queryClip(prompt.trim(), selectedVideoUuid);
      setSearchResults(frames);
      setSearchStatus('');
    } catch (error) {
      const errorResponse = error as { message?: string };
      setSearchError(errorResponse.message || 'Failed to search this video.');
    } finally {
      setIsSearching(false);
    }
  };

  const seekTo = (timestamp: number) => {
    const player = videoRef.current;
    if (!player) return;
    player.currentTime = timestamp;
    player.play().catch(() => undefined);
  };

  const formatTimestamp = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const rest = Math.floor(seconds % 60);
    return `${minutes}:${rest.toString().padStart(2, '0')}`;
  };

  const handlePromptChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPrompt(event.target.value);
    event.target.style.height = 'auto';
    event.target.style.height = `${event.target.scrollHeight}px`;
  };

  return (
    <>
      {selectedVideo ? (
        <>
          <div className="main-header-bar">
            <div className="main-header-title">{selectedVideo.title}</div>
            <div style={{ fontSize: '13px', color: 'var(--text)' }}>
              File: {selectedVideo.fileName}
            </div>
          </div>

          <div className="main-content-area">
            <div className="video-player-section">
              <div className="video-player-wrapper">
                <video
                  ref={videoRef}
                  className="video-player-element"
                  src={videoSrc || undefined}
                  controls
                />
              </div>

              {videoError && (
                <div className="local-file-relink-banner">
                  <span>
                    {videoError} Link the original file <strong>{selectedVideo.fileName}</strong> to play it locally.
                  </span>
                  <button className="relink-btn" onClick={() => relinkInputRef.current?.click()}>
                    Link File
                  </button>
                  <input
                    ref={relinkInputRef}
                    type="file"
                    accept="video/*"
                    style={{ display: 'none' }}
                    onChange={handleRelinkFile}
                  />
                </div>
              )}
            </div>

            {isSearching && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 24px',
                borderRadius: '8px',
                background: 'var(--accent-bg)',
                border: '1px solid var(--accent-border)',
                width: '100%',
                maxWidth: '800px',
                boxSizing: 'border-box',
              }}>
                <div className="spinner" style={{ borderTopColor: 'var(--accent)' }} />
                <span style={{ fontSize: '14px', color: 'var(--text-h)', fontWeight: 500 }}>
                  {searchStatus}
                </span>
              </div>
            )}

            {searchError && (
              <div className="alert alert-error" style={{ width: '100%', maxWidth: '800px', boxSizing: 'border-box' }}>
                <span>{searchError}</span>
              </div>
            )}

            {searchResults.length > 0 && (
              <div className="search-results-section">
                <h3 className="results-header">Matching Frames</h3>
                <div className="frame-result-grid">
                  {searchResults.map((frame, rank) => (
                    <button
                      key={frame.frame_id}
                      type="button"
                      className="frame-result-card"
                      onClick={() => seekTo(frame.timestamp)}
                      title={`Jump to ${formatTimestamp(frame.timestamp)}`}
                    >
                      {frame.thumbnail_url && (
                        <img src={frame.thumbnail_url} alt={`Frame at ${formatTimestamp(frame.timestamp)}`} loading="lazy" />
                      )}
                      <span className="frame-result-meta">
                        <span>{formatTimestamp(frame.timestamp)}</span>
                        <span className="frame-result-rank">#{rank + 1}</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="chat-prompt-section">
            <form onSubmit={handleSearchSubmit} className="chat-input-wrapper">
              <textarea
                className="chat-input-textarea"
                placeholder={`Ask Clip Search to find moments in "${selectedVideo.title}"... (e.g. "a person running")`}
                value={prompt}
                onChange={handlePromptChange}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    handleSearchSubmit(event);
                  }
                }}
                rows={1}
                disabled={isSearching}
              />
              <button
                type="submit"
                className="chat-submit-btn"
                disabled={!prompt.trim() || isSearching}
                aria-label="Search video"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22 2L11 13M22 2L15 22L11 13M11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </form>
            <div className="chat-prompt-hint">
              Describe the moment you are looking for. Press Enter to search.
            </div>
          </div>
        </>
      ) : (
        <div className="empty-state-container">
          <div className="empty-state-icon">🎬</div>
          <h2>Select a Video to Begin</h2>
          <p>
            Choose a video from the sidebar on the left, or register a new one to search matching visual moments using AI prompts.
          </p>
        </div>
      )}
    </>
  );
};

export default Video;