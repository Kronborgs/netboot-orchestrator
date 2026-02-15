/**
 * API client helper - ensures all requests use the correct host
 */

export const getApiUrl = (path: string): string => {
  // Use the same host as the frontend, but port 8000 for API
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  return `${protocol}//${hostname}:8000${path}`;
};

export const apiFetch = async (path: string, options?: RequestInit) => {
  const url = getApiUrl(path);
  return fetch(url, options);
};
