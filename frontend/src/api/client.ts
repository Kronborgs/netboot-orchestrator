/**
 * API client helper - ensures all requests use the correct host
 */

export const getApiUrl = (path: string): string => {
  // Use the same host as the frontend, but port 8000 for API
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  return `${protocol}//${hostname}:8000${path}`;
};

const TOKEN_KEY = 'nb_token';

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string): void => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = (): void => localStorage.removeItem(TOKEN_KEY);

export const apiFetch = async (path: string, options?: RequestInit) => {
  const url = getApiUrl(path);
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return fetch(url, { ...options, headers });
};
