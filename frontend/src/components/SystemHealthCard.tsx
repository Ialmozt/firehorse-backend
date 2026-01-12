import React from 'react';
import {
  Box,
  Badge,
  Text,
  HStack,
  VStack,
  Tooltip,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon, TimeIcon, NotAllowedIcon } from '@chakra-ui/icons';
import { api } from '../services/api';
import { useQuery } from '@tanstack/react-query';

export const SystemHealthCard: React.FC = () => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const { data, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await api.health.get();
      return response.data;
    },
    refetchInterval: 30000, // Обновлять каждые 30 секунд
  });

  const health = data?.data;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'green';
      case 'degraded':
        return 'yellow';
      case 'unhealthy':
        return 'red';
      default:
        return 'gray';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return CheckCircleIcon;
      case 'degraded':
        return WarningIcon;
      case 'unhealthy':
        return NotAllowedIcon;
      default:
        return TimeIcon;
    }
  };

  const getDatabaseStatus = (dbStatus: string) => {
    return dbStatus === 'connected' ? 'Подключена' : 'Отключена';
  };

  if (isLoading) {
    return (
      <Box
        p={4}
        bg={bgColor}
        border="1px"
        borderColor={borderColor}
        borderRadius="lg"
        minW="250px"
      >
        <HStack spacing={3}>
          <TimeIcon color="gray.500" />
          <Text fontSize="sm">Проверка состояния...</Text>
        </HStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        p={4}
        bg={bgColor}
        border="1px"
        borderColor={borderColor}
        borderRadius="lg"
        minW="250px"
      >
        <HStack spacing={3}>
          <NotAllowedIcon color="red.500" />
          <Text fontSize="sm" color="red.500">
            Ошибка проверки
          </Text>
        </HStack>
      </Box>
    );
  }

  return (
    <Box
      p={4}
      bg={bgColor}
      border="1px"
      borderColor={borderColor}
      borderRadius="lg"
      minW="250px"
    >
      <VStack align="start" spacing={2}>
        <HStack justifyContent="space-between" width="100%">
          <Text fontSize="sm" fontWeight="medium">
            Состояние системы
          </Text>
          <Badge
            colorScheme={getStatusColor(health?.status || 'unknown')}
            display="flex"
            alignItems="center"
            gap={1}
          >
            <Icon as={getStatusIcon(health?.status || 'unknown')} boxSize={3} />
            {health?.status === 'healthy' ? 'Работает' : 
             health?.status === 'degraded' ? 'Снижена' : 
             health?.status === 'unhealthy' ? 'Не работает' : 'Неизвестно'}
          </Badge>
        </HStack>

        <Box width="100%">
          <HStack justifyContent="space-between">
            <Text fontSize="xs" color="gray.600">
              База данных:
            </Text>
            <Badge
              colorScheme={health?.database === 'connected' ? 'green' : 'red'}
              fontSize="xs"
            >
              {getDatabaseStatus(health?.database || 'disconnected')}
            </Badge>
          </HStack>

          <HStack justifyContent="space-between" mt={1}>
            <Text fontSize="xs" color="gray.600">
              Версия:
            </Text>
            <Text fontSize="xs" fontFamily="mono">
              {health?.version || 'Неизвестно'}
            </Text>
          </HStack>

          <HStack justifyContent="space-between" mt={1}>
            <Text fontSize="xs" color="gray.600">
              Время:
            </Text>
            <Tooltip label={health?.timestamp}>
              <Text fontSize="xs" cursor="help">
                {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : '--:--'}
              </Text>
            </Tooltip>
          </HStack>
        </Box>
      </VStack>
    </Box>
  );
};
