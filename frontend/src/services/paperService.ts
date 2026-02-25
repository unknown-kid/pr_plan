import api from './api';

export const paperService = {
  list: (params: { skip?: number; limit?: number; is_public?: boolean; include_deleted?: boolean; folder_id?: string }) =>
    api.get('/papers/', { params }),
  
  get: (id: string) => api.get(`/papers/${id}`),
  
  upload: (title: string, file: File) => {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('file', file);
    return api.post('/papers/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  
  update: (id: string, data: any) => api.put(`/papers/${id}`, data),
  
  delete: (id: string) => api.delete(`/papers/${id}`),
  
  restore: (id: string) => api.post(`/papers/${id}/restore`),
  
  exportCitation: (id: string, format: string) => 
    api.post(`/papers/${id}/export`, null, { params: { format } }),
  
  addTag: (id: string, tag: string) => api.post(`/papers/${id}/tags`, { tag }),
};

export const searchService = {
  search: (params: { query: string; page?: number; page_size?: number; sort_by?: string }) =>
    api.get('/search/papers', { params }),
  
  getSuggestions: (query: string) => api.get('/search/suggestions', { params: { query } }),
  
  getPopular: () => api.get('/search/popular'),
};

export const personalizationService = {
  getFavorites: () => api.get('/users/favorites'),
  addFavorite: (paperId: string) => api.post(`/users/favorites/${paperId}`),
  removeFavorite: (paperId: string) => api.delete(`/users/favorites/${paperId}`),
  
  getProgress: (paperId: string) => api.get(`/users/reading-progress/${paperId}`),
  updateProgress: (paperId: string, page: number, percentage: number) => 
    api.put(`/users/reading-progress/${paperId}`, null, { params: { current_page: page, progress_percentage: percentage } }),
  
  getNotes: (paperId?: string) => api.get('/users/notes', { params: { paper_id: paperId } }),
  createNote: (data: { paper_id: string; note_text: string; page_number?: number; highlighted_text?: string }) => 
    api.post('/users/notes', data),
};

export const chatService = {
  listSessions: () => api.get('/conversations/'),
  createSession: (paperId?: string) => 
    api.post('/conversations/', null, { params: { paper_id: paperId } }),
};
