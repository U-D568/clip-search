import axios from 'axios';

// Create a centralized axios instance for interacting with the backend API.
// Using baseURL pointing to localhost:8000 as specified by backend main.py configuration.
// withCredentials is set to true to ensure HttpOnly cookies (access_token, refresh_token)
// are properly sent with cross-origin requests.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to handle global errors and unauthorized sessions
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // If 401 Unauthorized occurs on a non-auth page, clear fake local session and redirect to login
    if (error.response?.status === 401) {
      const isAuthPage = window.location.pathname === '/login' || window.location.pathname === '/register';
      if (!isAuthPage) {
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }

    // Return structured error message
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred';
    return Promise.reject({
      status: error.response?.status,
      message,
      data: error.response?.data,
    });
  }
);

export const getWebSocketUrl = (path: string): string => {
  const apiBaseUrl = apiClient.defaults.baseURL || '';
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

  const fallbackUrl = import.meta.env.VITE_FALLBACK_API_URL || 'http://localhost:8000';
  const targetUrl = apiBaseUrl || fallbackUrl;
  let host = 'localhost:8000';

  try {
    const url = new URL(targetUrl);
    host = url.host;
  } catch {
    if (targetUrl.startsWith('http')) {
      const match = targetUrl.match(/^https?:\/\/([^/]+)/);
      if (match) host = match[1];
    } else {
      host = targetUrl;
    }
  }

  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${wsProtocol}//${host}${cleanPath}`;
};

export default apiClient;
