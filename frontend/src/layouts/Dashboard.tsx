import React, { useState, useEffect, useRef } from 'react';
import { Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Header from './Header';
import Sidebar from './Sidebar';
import VideoSidebar from '../pages/VideoSidebar';
import { getVideos } from '../api/video';

interface LocalVideoMeta {
  uuid: string;
  title: string;
  state: 'queued' | 'processing' | 'complete' | 'error';
  uploaded_time: string;
  fileName: string;
}

export interface DashboardContextType {
  videos: LocalVideoMeta[];
  setVideos: React.Dispatch<React.SetStateAction<LocalVideoMeta[]>>;
  sessionFiles: { [uuid: string]: File };
  setSessionFiles: React.Dispatch<React.SetStateAction<{ [uuid: string]: File }>>;
  selectedVideoUuid: string;
  setSelectedVideoUuid: React.Dispatch<React.SetStateAction<string>>;
  refreshVideos: () => Promise<LocalVideoMeta[]>;
}

export const Dashboard: React.FC = () => {
  const { getCurrentUser, logout } = useAuth();
  const user = getCurrentUser();


  // 1. Shared core data states for state-lifting across nested routes
  const [videos, setVideos] = useState<LocalVideoMeta[]>([]);
  const [sessionFiles, setSessionFiles] = useState<{ [uuid: string]: File }>({});
  const [selectedVideoUuid, setSelectedVideoUuid] = useState<string>('');

  const fetchVideos = async (): Promise<LocalVideoMeta[]> => {
    try {
      const data = await getVideos();
      const mapped: LocalVideoMeta[] = data.map(item => ({
        uuid: item.uuid,
        title: item.title,
        state: item.state,
        uploaded_time: item.uploaded_time,
        fileName: item.title,
      }));
      setVideos(mapped);
      return mapped;
    } catch (err) {
      console.error('Failed to fetch videos from backend:', err);
      return [];
    }
  };

  useEffect(() => {
    if (user) {
      fetchVideos();
    }
  }, [user?.username]);

  // 2. Sidebar structural states
  const [sidebarWidth, setSidebarWidth] = useState(300);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const isResizingRef = useRef(false);

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  const toggleSidebar = () => {
    if (isCollapsed) {
      setIsCollapsed(false);
      setIsTransitioning(true);
      setTimeout(() => {
        setIsTransitioning(false);
      }, 300);
    } else {
      setIsCollapsed(true);
      setIsTransitioning(false);
    }
  };

  const startResizing = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    setIsResizing(true);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingRef.current) return;
      const newWidth = Math.max(300, e.clientX);
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      if (isResizingRef.current) {
        isResizingRef.current = false;
        setIsResizing(false);
        document.body.style.cursor = 'default';
        document.body.style.userSelect = 'auto';
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  // 3. Render sidebar content dynamically based on the current active URL path
  const renderSidebarContent = () => {
    return (
      <VideoSidebar
        videos={videos}
        setSessionFiles={setSessionFiles}
        selectedVideoUuid={selectedVideoUuid}
        onSelectVideo={(uuid) => setSelectedVideoUuid(uuid)}
        refreshVideos={fetchVideos}
      />
    );
  };

  const contextValue: DashboardContextType = {
    videos,
    setVideos,
    sessionFiles,
    setSessionFiles,
    selectedVideoUuid,
    setSelectedVideoUuid,
    refreshVideos: fetchVideos
  };

  return (
    <>
      <Header
        user={user}
        isCollapsed={isCollapsed}
        onToggleSidebar={toggleSidebar}
        onLogout={handleLogout}
      />

      <div className="dashboard-layout">
        <Sidebar
          isCollapsed={isCollapsed}
          isTransitioning={isTransitioning}
          sidebarWidth={sidebarWidth}
          isResizing={isResizing}
          sidebarContent={renderSidebarContent()}
        />

        {/* Resizer Handle */}
        {!isCollapsed && (
          <div
            className="sidebar-resizer"
            onMouseDown={startResizing}
          />
        )}

        {/* Dynamic Nested View rendering using React Router Outlet */}
        <main className="dashboard-main">
          <Outlet context={contextValue} />
        </main>
      </div>
    </>
  );
};

export default Dashboard;
