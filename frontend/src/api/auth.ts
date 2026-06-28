import apiClient from './client';

// Map request interface matching Pydantic schema backend/app/schema/dto.py
export interface LoginRequest {
  username: string;
  password: string;
}

// Map response interfaces based on backend/app/routes/auth.py endpoints
export interface LoginResponse {
  username: string;
  result: string;
}

export interface RegisterResponse {
  username: string;
}

/**
 * Sends a request to login the user.
 * Backend endpoint: POST /auth/login
 */
export const loginUser = async (credentials: LoginRequest): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
  return response.data;
};

/**
 * Sends a request to register a new user.
 * Backend endpoint: POST /auth/register
 */
export const registerUser = async (credentials: LoginRequest): Promise<RegisterResponse> => {
  const response = await apiClient.post<RegisterResponse>('/auth/register', credentials);
  return response.data;
};
