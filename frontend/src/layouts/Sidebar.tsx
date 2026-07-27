import React from 'react';

interface SidebarProps {
  isCollapsed: boolean;
  isTransitioning: boolean;
  sidebarWidth: number;
  isResizing: boolean;
  sidebarContent: React.ReactNode;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  isTransitioning,
  sidebarWidth,
  isResizing,
  sidebarContent
}) => {
  const transitionClass = !isResizing ? 'sidebar-transition' : '';
  const collapsedClass = isCollapsed ? 'collapsed' : '';
  const transitioningClass = isTransitioning ? 'transitioning' : '';

  return (
    <aside 
      className={`dashboard-sidebar ${transitionClass} ${collapsedClass} ${transitioningClass}`}
      style={{ 
        width: isCollapsed ? 0 : `${sidebarWidth}px`, 
        minWidth: isCollapsed ? 0 : '300px',
        borderRightWidth: isCollapsed ? 0 : 1
      }}
    >
      {sidebarContent}
    </aside>
  );
};

export default Sidebar;
