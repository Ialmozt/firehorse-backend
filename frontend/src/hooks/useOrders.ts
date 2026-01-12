import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { Order } from '../types';

// Ключи для кэширования
export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (filters: any) => [...orderKeys.lists(), filters] as const,
  details: () => [...orderKeys.all, 'detail'] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
  stats: () => [...orderKeys.all, 'stats'] as const,
};

// Хук для получения списка заказов
export const useOrders = (page = 1, limit = 20) => {
  return useQuery({
    queryKey: orderKeys.list({ page, limit }),
    queryFn: async () => {
      const response = await api.orders.getAll(page, limit);
      return response.data;
    },
    staleTime: 10000, // 10 секунд
    refetchInterval: 30000, // Авто-обновление каждые 30 секунд
  });
};

// Хук для получения заказа по ID
export const useOrder = (id: string) => {
  return useQuery({
    queryKey: orderKeys.detail(id),
    queryFn: async () => {
      const response = await api.orders.getById(id);
      return response.data;
    },
    enabled: !!id, // Запрос выполняется только если id существует
  });
};

// Хук для создания заказа
export const useCreateOrder = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (orderData: Partial<Order>) => {
      const response = await api.orders.create(orderData);
      return response.data;
    },
    onSuccess: () => {
      // Инвалидируем кэш списка заказов
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      // Инвалидируем кэш статистики
      queryClient.invalidateQueries({ queryKey: orderKeys.stats() });
    },
  });
};

// Хук для обновления заказа
export const useUpdateOrder = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Order> }) => {
      const response = await api.orders.update(id, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Инвалидируем кэш конкретного заказа
      queryClient.invalidateQueries({ queryKey: orderKeys.detail(variables.id) });
      // Инвалидируем кэш списка заказов
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });
};

// Хук для удаления заказа
export const useDeleteOrder = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.orders.delete(id);
      return response.data;
    },
    onSuccess: (_, id) => {
      // Удаляем заказ из кэша
      queryClient.removeQueries({ queryKey: orderKeys.detail(id) });
      // Инвалидируем кэш списка заказов
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      // Инвалидируем кэш статистики
      queryClient.invalidateQueries({ queryKey: orderKeys.stats() });
    },
  });
};

// Хук для получения статистики
export const useOrderStats = () => {
  return useQuery({
    queryKey: orderKeys.stats(),
    queryFn: async () => {
      const response = await api.stats.get();
      return response.data;
    },
    staleTime: 30000, // 30 секунд
    refetchInterval: 60000, // Авто-обновление каждую минуту
  });
};
