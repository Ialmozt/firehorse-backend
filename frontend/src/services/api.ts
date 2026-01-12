import axios from 'axios';
import type { AxiosInstance, AxiosResponse } from 'axios';
import type { Order, OrderStats, SystemHealth, ApiResponse, PaginatedResponse } from '../types';

// Базовый URL API
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Создание экземпляра axios с настройками
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  timeout: 10000, // 10 секунд таймаут
});

// Интерцептор для обработки ошибок
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Проверяем структуру ответа
    if (response.data && typeof response.data === 'object') {
      return response;
    }
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    
    // Обработка различных типов ошибок
    if (error.response) {
      // Сервер ответил с ошибкой
      const { status, data } = error.response;
      
      if (status === 401) {
        console.error('Unauthorized access');
      } else if (status === 403) {
        console.error('Forbidden');
      } else if (status === 404) {
        console.error('Resource not found');
      } else if (status >= 500) {
        console.error('Server error');
      }
      
      return Promise.reject({
        status,
        message: data?.error || data?.message || 'Unknown error',
        data: data,
      });
    } else if (error.request) {
      // Запрос был сделан, но ответ не получен
      console.error('Network error - no response received');
      return Promise.reject({
        status: 0,
        message: 'Network error. Please check your connection.',
      });
    } else {
      // Ошибка при настройке запроса
      console.error('Request setup error:', error.message);
      return Promise.reject({
        status: -1,
        message: error.message || 'Request setup failed',
      });
    }
  }
);

// API методы
export const api = {
  // Health check
  health: {
    get: (): Promise<AxiosResponse<ApiResponse<SystemHealth>>> => 
      apiClient.get('/health'),
  },

  // Orders
  orders: {
    getAll: (page = 1, limit = 20): Promise<AxiosResponse<ApiResponse<PaginatedResponse<Order>>>> =>
      apiClient.get(`/api/orders?page=${page}&limit=${limit}`),
    
    getById: (id: string): Promise<AxiosResponse<ApiResponse<Order>>> =>
      apiClient.get(`/api/orders/${id}`),
    
    create: (orderData: Partial<Order>): Promise<AxiosResponse<ApiResponse<Order>>> =>
      apiClient.post('/api/orders', orderData),
    
    update: (id: string, orderData: Partial<Order>): Promise<AxiosResponse<ApiResponse<Order>>> =>
      apiClient.put(`/api/orders/${id}`, orderData),
    
    delete: (id: string): Promise<AxiosResponse<ApiResponse<void>>> =>
      apiClient.delete(`/api/orders/${id}`),
  },

  // Statistics
  stats: {
    get: (): Promise<AxiosResponse<ApiResponse<OrderStats>>> =>
      apiClient.get('/api/stats'),
    
    getRecent: (hours = 24): Promise<AxiosResponse<ApiResponse<any>>> =>
      apiClient.get(`/api/stats/recent?hours=${hours}`),
  },

  // Events
  events: {
    getByOrderId: (orderId: string): Promise<AxiosResponse<ApiResponse<any[]>>> =>
      apiClient.get(`/api/events/order/${orderId}`),
    
    getRecent: (limit = 50): Promise<AxiosResponse<ApiResponse<any[]>>> =>
      apiClient.get(`/api/events/recent?limit=${limit}`),
  },

  // System
  system: {
    metrics: (): Promise<AxiosResponse<string>> =>
      apiClient.get('/metrics', {
        headers: { 'Accept': 'text/plain' },
      }),
    
    logs: (limit = 100): Promise<AxiosResponse<ApiResponse<any[]>>> =>
      apiClient.get(`/api/logs?limit=${limit}`),
  },
};

// Экспорт экземпляра для прямого доступа
export default apiClient;
