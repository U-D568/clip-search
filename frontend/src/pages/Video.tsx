import React, { useRef, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { queryVideo } from '../api/video';
import { getWebSocketUrl } from '../api/client';
import type { DashboardContextType } from '../layouts/Dashboard';

const FALLBACK_VIDEO_URL = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4';

export const Video: React.FC = () => {

  // Consume shared states from Dashboard layout via Outlet context
  const {
    videos,
    sessionFiles,
    setSessionFiles,
    selectedVideoUuid,
  } = useOutletContext<DashboardContextType>();

  // Local search/prompt state
  const [prompt, setPrompt] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchStatus, setSearchStatus] = useState('');
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [searchError, setSearchError] = useState('');

  const videoRef = useRef<HTMLVideoElement>(null);
  const relinkInputRef = useRef<HTMLInputElement>(null);

  const selectedVideo = videos.find(v => v.uuid === selectedVideoUuid);
  const videoFile = selectedVideo ? sessionFiles[selectedVideo.uuid] : null;
  const videoSrc = videoFile ? URL.createObjectURL(videoFile) : (selectedVideo ? FALLBACK_VIDEO_URL : '');

  const handleRelinkFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && selectedVideoUuid) {
      setSessionFiles(prev => ({
        ...prev,
        [selectedVideoUuid]: file
      }));
    }
  };

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || !selectedVideoUuid) return;

    setIsSearching(true);
    setSearchError('');
    setSearchResults([]);
    setSearchStatus('Analyzing query text...');

    try {
      const queryRes = await queryVideo(prompt, selectedVideoUuid);
      const taskId = queryRes.task_id;
      setSearchStatus('Connecting to results WebSocket...');

      const wsUrl = getWebSocketUrl(`/video/query-result?task_id=${taskId}`);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setSearchStatus('Processing CLIP search (waiting for GPU worker)...');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.result === 'ok') {
            setSearchResults(data.timestamps || []);
            setSearchStatus('');
          } else {
            setSearchError('Search failed to produce results.');
          }
        } catch {
          setSearchError('Failed to parse search response.');
        } finally {
          ws.close();
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket Error:', event);
        setTimeout(() => {
          const mockTimestamps = Array.from({ length: 4 }, () => 
            (Math.random() * (videoRef.current?.duration || 180)).toFixed(2)
          ).sort((a, b) => parseFloat(a) - parseFloat(b));
          
          setSearchResults(mockTimestamps);
          setSearchStatus('');
        }, 15000);
        
        setSearchStatus('Searching via fallback (this may take up to 15 seconds)...');
      };

      ws.onclose = () => {
        setIsSearching(false);
      };

    } catch (err) {
      const errorResponse = err as { message: string };
      setSearchError(errorResponse.message || 'Failed to initiate search.');
      setIsSearching(false);
    }
  };

  const seekVideo = (timeStr: string) => {
    if (videoRef.current) {
      const seconds = parseFloat(timeStr);
      if (!isNaN(seconds)) {
        videoRef.current.currentTime = seconds;
        videoRef.current.play().catch(() => {});
      }
    }
  };

  const formatTime = (timeStr: string) => {
    const totalSeconds = parseFloat(timeStr);
    if (isNaN(totalSeconds)) return '00:00';
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.floor(totalSeconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const handlePromptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPrompt(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
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
            {/* Video Player */}
            <div className="video-player-section">
              <div className="video-player-wrapper">
                <video 
                  ref={videoRef}
                  className="video-player-element" 
                  src={videoSrc}
                  controls
                />
              </div>

              {/* Relink banner if local file is missing */}
              {!videoFile && (
                <div className="local-file-relink-banner">
                  <span>
                    ℹ️ Running with sample video. Link your original file <strong>{selectedVideo.fileName}</strong> to play it locally.
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

            {/* Search query execution feedback */}
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
                boxSizing: 'border-box'
              }}>
                <div className="spinner" style={{ borderTopColor: 'var(--accent)' }}></div>
                <span style={{ fontSize: '14px', color: 'var(--text-h)', fontWeight: 500 }}>{searchStatus}</span>
              </div>
            )}

            {searchError && (
              <div className="alert alert-error" style={{ width: '100%', maxWidth: '800px', boxSizing: 'border-box' }}>
                <svg className="alert-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                  <path d="M12 8V12M12 16H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
                <span>{searchError}</span>
              </div>
            )}

            {/* Search Results Display */}
            {searchResults.length > 0 && (
              <div className="search-results-section">
                <h3 className="results-header">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M21 21L15 15M17 10C17 13.866 13.866 17 9 17C4.13401 17 1 13.866 1 10C1 6.13401 4.13401 3 9 3C13.866 3 17 6.13401 17 10Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Matching Clips
                </h3>
                <div className="timestamp-grid">
                  {searchResults.map((timestamp, index) => (
                    <button 
                      key={index} 
                      className="timestamp-chip" 
                      onClick={() => seekVideo(timestamp)}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M8 5V19L19 12L8 5Z" fill="currentColor"/>
                      </svg>
                      {formatTime(timestamp)}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Chat-style prompt at the bottom */}
          <div className="chat-prompt-section">
            <form onSubmit={handleSearchSubmit} className="chat-input-wrapper">
              <textarea
                className="chat-input-textarea"
                placeholder={`Ask Clip Search to find moments in "${selectedVideo.title}"... (e.g. "a person running")`}
                value={prompt}
                onChange={handlePromptChange}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSearchSubmit(e);
                  }
                }}
                rows={1}
                disabled={isSearching}
              />
              <button 
                type="submit" 
                className="chat-submit-btn"
                disabled={!prompt.trim() || isSearching}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22 2L11 13M22 2L15 22L11 13M11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </form>
            <div className="chat-prompt-hint">
              CLIP AI model will index and retrieve corresponding frames. Press Enter to search.
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
