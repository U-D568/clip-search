import { useState } from 'react';
import { loginUser, registerUser } from '../api/auth';
import type { LoginRequest } from '../api/auth';

export const useAuth = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const login = async (data: LoginRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await loginUser(data);
      // Store user information in localStorage for state persistence
      localStorage.setItem('user', JSON.stringify({ username: response.username }));
      return response;
    } catch (err) {
      const errorResponse = err as { message: string };
      setError(errorResponse.message || 'Failed to login');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (data: LoginRequest) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await registerUser(data);
      setSuccess('Registration successful! Redirecting to login...');
      return response;
    } catch (err) {
      const errorResponse = err as {
        message: string;
        data?: { status_code?: number; detail?: string };
      };
      // Handle edge cases in backend where FastAPI returns an HTTPException directly instead of raising it.
      // E.g., @auth_router.post("/register") returns HTTPException(401, "User Already Exists") directly.
      // If FastAPI returns it directly, it could be a 200 OK containing {"status_code": 401, "detail": "User Already Exists"}.
      // We check for that custom payload structure.
      if (errorResponse.data && errorResponse.data.status_code && errorResponse.data.detail) {
        setError(errorResponse.data.detail);
        throw new Error(errorResponse.data.detail, { cause: err });
      } else {
        setError(errorResponse.message || 'Failed to register');
        throw err;
      }
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('user');
  };

  const getCurrentUser = () => {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  };

  return {
    login,
    register,
    logout,
    getCurrentUser,
    loading,
    error,
    success,
    setError,
  };
};
