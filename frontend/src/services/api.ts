import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export interface AuthResponse {
  access: string;
  refresh: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface FileRevision {
  id: number;
  revision_number: number;
  uploaded_at: string;
  file_size: number;
  formatted_file_size: string;
  file_extension: string;
  content_type: string;
}

export interface FileDocument {
  id: number;
  url: string;
  name: string;
  created_at: string;
  updated_at: string;
  latest_revision?: FileRevision;
  revision_count: number;
  revisions?: FileRevision[];
}

export const authAPI = {
  login: (username: string, password: string) =>
    api.post<AuthResponse>('/auth/login/', { username, password }),
  
  register: (userData: {
    username: string;
    email: string;
    password: string;
    password_confirm: string;
    first_name?: string;
    last_name?: string;
  }) => api.post('/auth/register/', userData),
  
  logout: () => api.post('/auth/logout/'),
  
  profile: () => api.get<User>('/auth/profile/'),
};

export interface FileListResponse {
  count: number;
  results: FileDocument[];
}

export const filesAPI = {
  list: () => api.get<FileListResponse>('/files/'),
  
  upload: (formData: FormData) => {
    return api.post<FileDocument>('/files/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  uploadNewVersion: (fileUrl: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.put<FileDocument>(`/files/${fileUrl}/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  get: (url: string) => api.get<FileDocument>(`/files/${url}/`),
  
  delete: (url: string) => api.delete(`/files/${url}/`),
  
  download: (url: string, revisionNumber?: number) => {
    const downloadUrl = revisionNumber 
      ? `/files/${url}/?download=true&revision=${revisionNumber}`
      : `/files/${url}/?download=true`;
    
    console.log('Making download request:', {
      originalUrl: url,
      revisionNumber,
      fullDownloadUrl: downloadUrl
    });
    
    return api.get(downloadUrl, {
      responseType: 'blob',
    });
  },
  
  getRevisions: (url: string) => api.get<{document: FileDocument, revisions: FileRevision[]}>(`/files/${url}/revisions/`),
};

export default api;