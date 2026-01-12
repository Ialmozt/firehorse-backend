import React from 'react';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import { Box, Text, useColorModeValue, Skeleton } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';

interface RevenueData {
  date: string;
  revenue: number;
  orders: number;
}

export const RevenueChart: React.FC = () => {
  const textColor = useColorModeValue('gray.800', 'gray.200');
  const gridColor = useColorModeValue('#e5e7eb', '#374151');
  const lineColor = useColorModeValue('#3b82f6', '#60a5fa');
  const areaColor = useColorModeValue('#93c5fd', '#1e40af');

  const { data, isLoading, error } = useQuery({
    queryKey: ['revenue-chart'],
    queryFn: async () => {
      // Временные данные, пока нет реального API
      const today = new Date();
      const data: RevenueData[] = [];
      
      // Генерация данных за последние 7 дней
      for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(today.getDate() - i);
        
        data.push({
          date: date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' }),
          revenue: Math.floor(Math.random() * 5000) + 1000,
          orders: Math.floor(Math.random() * 50) + 10,
        });
      }
      
      return { data };
    },
    refetchInterval: 300000, // Обновлять каждые 5 минут
  });

  if (isLoading) {
    return <Skeleton height="300px" borderRadius="md" />;
  }

  if (error) {
    return (
      <Box p={4} textAlign="center">
        <Text color="red.500">Ошибка загрузки данных графика</Text>
      </Box>
    );
  }

  const chartData = data?.data || [];

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Box
          bg={useColorModeValue('white', 'gray.800')}
          p={3}
          border="1px"
          borderColor={useColorModeValue('gray.200', 'gray.700')}
          borderRadius="md"
          boxShadow="lg"
        >
          <Text fontWeight="bold" mb={1}>
            {label}
          </Text>
          <Text color={lineColor}>
            Выручка: {formatCurrency(payload[0].value)}
          </Text>
          <Text color="#10b981">
            Заказы: {payload[1].value}
          </Text>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box height="300px">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke={gridColor}
            vertical={false}
          />
          <XAxis 
            dataKey="date" 
            stroke={textColor}
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <YAxis 
            stroke={textColor}
            fontSize={12}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `$${value}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Area
            type="monotone"
            dataKey="revenue"
            stroke={lineColor}
            fill={areaColor}
            fillOpacity={0.3}
            strokeWidth={2}
            name="Выручка"
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="orders"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
            name="Заказы"
          />
        </AreaChart>
      </ResponsiveContainer>
    </Box>
  );
};
