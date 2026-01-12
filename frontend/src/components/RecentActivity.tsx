import React from 'react';
import {
  VStack,
  HStack,
  Text,
  Box,
  Icon,
  Badge,
  Avatar,
  useColorModeValue,
  Skeleton,
} from '@chakra-ui/react';
import {
  CheckCircleIcon,
  WarningIcon,
  TimeIcon,
  ChatIcon,
  ArrowForwardIcon,
} from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';

interface ActivityItem {
  id: string;
  type: 'order' | 'system' | 'error' | 'info';
  message: string;
  user?: string;
  timestamp: string;
  status?: 'success' | 'warning' | 'error' | 'info';
}

export const RecentActivity: React.FC = () => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const { data, isLoading, error } = useQuery({
    queryKey: ['recent-activity'],
    queryFn: async () => {
      // Временные данные, пока нет реального API
      return {
        data: [
          {
            id: '1',
            type: 'order' as const,
            message: 'Новый заказ создан',
            user: 'Иван Петров',
            timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(), // 5 минут назад
            status: 'success' as const,
          },
          {
            id: '2',
            type: 'system' as const,
            message: 'Автоматическая обработка завершена',
            timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(), // 15 минут назад
            status: 'info' as const,
          },
          {
            id: '3',
            type: 'error' as const,
            message: 'Ошибка подключения к DeepSeek API',
            timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 минут назад
            status: 'error' as const,
          },
          {
            id: '4',
            type: 'order' as const,
            message: 'Заказ #12345 отправлен на доработку',
            user: 'Анна Сидорова',
            timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(), // 45 минут назад
            status: 'warning' as const,
          },
          {
            id: '5',
            type: 'system' as const,
            message: 'Ежедневный бэкап выполнен',
            timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(), // 1 час назад
            status: 'success' as const,
          },
        ],
      };
    },
    refetchInterval: 60000, // Обновлять каждую минуту
  });

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'success':
        return CheckCircleIcon;
      case 'warning':
        return WarningIcon;
      case 'error':
        return WarningIcon;
      case 'info':
        return ChatIcon;
      default:
        return TimeIcon;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'success':
        return 'green';
      case 'warning':
        return 'yellow';
      case 'error':
        return 'red';
      case 'info':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const formatTime = (timestamp: string) => {
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now.getTime() - time.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'только что';
    if (diffMins < 60) return `${diffMins} мин назад`;
    if (diffHours < 24) return `${diffHours} ч назад`;
    return `${diffDays} дн назад`;
  };

  if (isLoading) {
    return (
      <VStack spacing={3} align="stretch">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height="60px" borderRadius="md" />
        ))}
      </VStack>
    );
  }

  if (error) {
    return (
      <Box p={4} textAlign="center">
        <Text color="red.500">Ошибка загрузки активности</Text>
      </Box>
    );
  }

  const activities: ActivityItem[] = data?.data || [];

  return (
    <VStack spacing={3} align="stretch" maxH="400px" overflowY="auto">
      {activities.map((activity) => (
        <Box
          key={activity.id}
          p={3}
          bg={bgColor}
          border="1px"
          borderColor={borderColor}
          borderRadius="md"
          _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }}
        >
          <HStack spacing={3} align="start">
            <Icon
              as={getStatusIcon(activity.status)}
              color={`${getStatusColor(activity.status)}.500`}
              boxSize={5}
              mt={1}
            />
            <Box flex={1}>
              <Text fontSize="sm" mb={1}>
                {activity.message}
              </Text>
              <HStack spacing={2}>
                {activity.user && (
                  <HStack spacing={1}>
                    <Avatar size="xs" name={activity.user} />
                    <Text fontSize="xs" color="gray.600">
                      {activity.user}
                    </Text>
                  </HStack>
                )}
                <Text fontSize="xs" color="gray.500">
                  {formatTime(activity.timestamp)}
                </Text>
                <Badge
                  size="sm"
                  colorScheme={getStatusColor(activity.status)}
                  variant="subtle"
                >
                  {activity.type === 'order' ? 'Заказ' : 
                   activity.type === 'system' ? 'Система' : 
                   activity.type === 'error' ? 'Ошибка' : 'Инфо'}
                </Badge>
              </HStack>
            </Box>
            <ArrowForwardIcon color="gray.400" boxSize={4} />
          </HStack>
        </Box>
      ))}
    </VStack>
  );
};
