import React from 'react';
import {
  Box,
  Grid,
  GridItem,
  Heading,
  Text,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Flex,
  useColorModeValue,
  Card,
  CardBody,
  SimpleGrid,
} from '@chakra-ui/react';
import { useOrderStats } from '../hooks/useOrders';
import { SystemHealthCard } from './SystemHealthCard';
import { OrdersTable } from './OrdersTable';
import { RecentActivity } from './RecentActivity';
import { RevenueChart } from './RevenueChart';

export const Dashboard: React.FC = () => {
  const { data: statsData, isLoading, error } = useOrderStats();
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const stats = statsData?.data || {
    total: 0,
    queued: 0,
    processing: 0,
    completed: 0,
    failed: 0,
    today: 0,
    revenue: 0,
  };

  const statCards = [
    {
      label: 'Всего заказов',
      value: stats.total,
      change: '+12%',
      isPositive: true,
      color: 'blue',
    },
    {
      label: 'В обработке',
      value: stats.processing,
      change: '+5%',
      isPositive: true,
      color: 'yellow',
    },
    {
      label: 'Завершено',
      value: stats.completed,
      change: '+8%',
      isPositive: true,
      color: 'green',
    },
    {
      label: 'Выручка',
      value: `$${stats.revenue.toLocaleString()}`,
      change: '+15%',
      isPositive: true,
      color: 'purple',
    },
  ];

  if (isLoading) {
    return (
      <Box p={6}>
        <Text>Загрузка статистики...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <Text color="red.500">Ошибка загрузки статистики: {error.message}</Text>
      </Box>
    );
  }

  return (
    <Box p={6}>
      <Flex justifyContent="space-between" alignItems="center" mb={8}>
        <Box>
          <Heading size="lg" mb={2}>
            Панель управления Firehorse
          </Heading>
          <Text color="gray.600">
            Мониторинг и управление автоматической обработкой заказов
          </Text>
        </Box>
        <SystemHealthCard />
      </Flex>

      {/* Статистика */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
        {statCards.map((stat, index) => (
          <Card key={index} bg={bgColor} border="1px" borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel fontSize="sm" color="gray.600">
                  {stat.label}
                </StatLabel>
                <StatNumber fontSize="2xl" fontWeight="bold">
                  {stat.value}
                </StatNumber>
                <StatHelpText>
                  <StatArrow type={stat.isPositive ? 'increase' : 'decrease'} />
                  {stat.change}
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        ))}
      </SimpleGrid>

      <Grid templateColumns={{ base: '1fr', lg: '2fr 1fr' }} gap={6} mb={8}>
        {/* График выручки */}
        <GridItem>
          <Card bg={bgColor} border="1px" borderColor={borderColor} height="100%">
            <CardBody>
              <Heading size="md" mb={4}>
                Выручка по дням
              </Heading>
              <RevenueChart />
            </CardBody>
          </Card>
        </GridItem>

        {/* Последняя активность */}
        <GridItem>
          <Card bg={bgColor} border="1px" borderColor={borderColor} height="100%">
            <CardBody>
              <Heading size="md" mb={4}>
                Последняя активность
              </Heading>
              <RecentActivity />
            </CardBody>
          </Card>
        </GridItem>
      </Grid>

      {/* Таблица заказов */}
      <Card bg={bgColor} border="1px" borderColor={borderColor}>
        <CardBody>
          <Heading size="md" mb={4}>
            Последние заказы
          </Heading>
          <OrdersTable />
        </CardBody>
      </Card>
    </Box>
  );
};
