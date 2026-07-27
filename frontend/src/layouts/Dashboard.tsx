import React, { useState, useEffect, useRef } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Header from './Header';
import Sidebar from './Sidebar';
import VideoSidebar from '../pages/VideoSidebar';

interface LocalVideoMeta {
  uuid: string;
  title: string;
  state: 'queued' | 'in_progress' | 'complete' | 'f_complete' | 'error';
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
}

export const Dashboard: React.FC = () => {
  const { getCurrentUser, logout } = useAuth();
  const user = getCurrentUser();
  const location = useLocation();

  // 1. Shared core data states for state-lifting across nested routes
  const [videos, setVideos] = useState<LocalVideoMeta[]>(() => {
    if (user) {
      const saved = localStorage.getItem(`videos_${user.username}`);
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          console.error(e);
        }
      }
    }
    return [];
  });

  const [sessionFiles, setSessionFiles] = useState<{ [uuid: string]: File }>({});
  const [selectedVideoUuid, setSelectedVideoUuid] = useState<string>('');

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
    // We display VideoSidebar for the home path (/)
    if (location.pathname === '/' || location.pathname === '') {
      return (
        <VideoSidebar
          videos={videos}
          setVideos={setVideos}
          setSessionFiles={setSessionFiles}
          selectedVideoUuid={selectedVideoUuid}
          onSelectVideo={(uuid) => setSelectedVideoUuid(uuid)}
        />
      );
    }
    // Expandable: return specific sidebars for other routes (e.g. settings sidebar)
    return null;
  };

  const contextValue: DashboardContextType = {
    videos,
    setVideos,
    sessionFiles,
    setSessionFiles,
    selectedVideoUuid,
    setSelectedVideoUuid
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
