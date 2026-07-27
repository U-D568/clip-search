import React from 'react';
import { Menu } from 'lucide-react';

interface HeaderProps {
  user: { username: string } | null;
  isCollapsed: boolean;
  onToggleSidebar: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({ user, isCollapsed, onToggleSidebar, onLogout }) => {
  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '16px 32px',
      borderBottom: '1px solid var(--border)',
      height: '60px',
      boxSizing: 'border-box'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {user && (
          <button
            className="sidebar-toggle-btn"
            style={{ marginRight: '4px' }}
            onClick={onToggleSidebar}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <Menu size={20} />
          </button>
        )}
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M19 12C19 15.866 15.866 19 12 19C8.13401 19 5 15.866 5 12C5 8.13401 8.13401 5 12 5C15.866 5 19 8.13401 19 12Z" stroke="var(--accent)" strokeWidth="2" />
          <path d="M12 8V12L15 15" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <span style={{ fontWeight: 600, color: 'var(--text-h)' }}>CLIP Search</span>
      </div>
      {user && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontSize: '14px', color: 'var(--text)' }}>
            Logged in as <strong style={{ color: 'var(--text-h)' }}>{user.username}</strong>
          </span>
          <button
            onClick={onLogout}
            style={{
              background: 'var(--code-bg)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '6px 12px',
              cursor: 'pointer',
              fontSize: '14px',
              color: 'var(--text-h)',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--border)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'var(--code-bg)'}
          >
            Sign Out
          </button>
        </div>
      )}
    </header>
  );
};

export default Header;
