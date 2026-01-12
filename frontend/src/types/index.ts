// Типы данных для Firehorse MVP

export interface Order {
  id: string;
  source_id: string;
  topic: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  customer: string;
  amount: number;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface OrderEvent {
  id: string;
  order_id: string;
  stage: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
  created_at: string;
}

export interface OrderStats {
  total: number;
  queued: number;
  processing: number;
  completed: number;
  failed: number;
  today: number;
  revenue: number;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  database: 'connected' | 'disconnected';
  version: string;
  timestamp: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: string | null;
  meta: {
    timestamp: string;
    version: string;
    trace_id: string;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
}
