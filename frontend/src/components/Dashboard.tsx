import React, { useState } from 'react';
import {
  Box,
  SimpleGrid,
  Card,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Text,
  useColorModeValue,
  Button,
  HStack,
} from '@chakra-ui/react';
import { RevenueChart } from './RevenueChart';
import { OrdersTable } from './OrdersTable';
import { RecentActivity } from './RecentActivity';
import { SystemHealthCard } from './SystemHealthCard';
import { MetricsPanel } from './MetricsPanel';
import { DeepSeekUsage } from './DeepSeekUsage';
import { TestOrderButton } from './TestOrderButton';
import { ManualOrderDialog } from './ManualOrderDialog';
import { useOrderStats } from '../hooks/useOrders';
import { AddIcon } from '@chakra-ui/icons';

export const Dashboard: React.FC = () => {
  const { data: statsData, isLoading, error } = useOrderStats();
  const [isManualOrderOpen, setIsManualOrderOpen] = useState(false);
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
      value: `$${(stats.revenue || 0).toLocaleString()}`,
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
        <Text color="red.500">Ошибка загрузки статистики</Text>
      </Box>
    );
  }

  return (
    <Box p={6}>
      {/* 🔥 HARDCODE MANUAL ORDER - ГАРАНТИРОВАННАЯ КНОПКА */}
      <Box 
        mb={8} 
        p={6} 
        bgGradient="linear(to-r, blue.600, purple.600)" 
        borderRadius="2xl" 
        color="white" 
        boxShadow="2xl"
      >
        <Text fontSize="2xl" fontWeight="bold" mb={4}>
          🚀 MANUAL ORDER TEST (HARDCODE)
        </Text>
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
          <input 
            id="hardcode-kworkid" 
            placeholder="kwork-001" 
            style={{ 
              padding: '12px',
              borderRadius: '12px',
              color: 'black',
              width: '100%',
              border: 'none'
            }}
          />
          <input 
            id="hardcode-topic" 
            placeholder="1500 слов статья" 
            style={{ 
              padding: '12px',
              borderRadius: '12px',
              color: 'black',
              width: '100%',
              border: 'none'
            }}
          />
          <Button 
            onClick={() => {
              const id = (document.getElementById('hardcode-kworkid') as HTMLInputElement)?.value;
              const topic = (document.getElementById('hardcode-topic') as HTMLInputElement)?.value;
              if (!id || !topic) {
                alert('Заполни ID + Topic!');
                return;
              }
              
              const btn = event?.target as HTMLButtonElement;
              const originalText = btn.innerHTML;
              btn.innerHTML = '⏳ Отправка...';
              btn.disabled = true;
              
              fetch('http://localhost:8000/webhook', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-Token': '44c89b6265fb03bb6ce22c5f41f02bca87177662da81e3ed719c7321b36f8a70'
                },
                body: JSON.stringify({ kworkid: id, topic: topic })
              })
              .then(res => res.json())
              .then(data => {
                if (data.orderid) {
                  alert(`✅ Заказ создан!\nID: ${data.orderid}\n\n📊 Мониторь в Grafana: localhost:3000`);
                } else {
                  alert(`❌ Ошибка: ${JSON.stringify(data)}`);
                }
              })
              .catch(e => {
                alert(`❌ Network error: ${e}`);
              })
              .finally(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
              });
            }}
            bg="white"
            color="blue.600"
            p={3}
            borderRadius="xl"
            fontWeight="bold"
            _hover={{ boxShadow: 'lg' }}
            gridColumn={{ base: 1, md: 'span 2' }}
            width="100%"
          >
            ➕ ОТПРАВИТЬ В FIREHORSE (1 сек)
          </Button>
        </SimpleGrid>
      </Box>

      {/* Кнопки создания заказов */}
      <Box display="flex" justifyContent="flex-end" mb={4} gap={3}>
        <TestOrderButton />
        <Button
          leftIcon={<AddIcon />}
          colorScheme="blue"
          onClick={() => setIsManualOrderOpen(true)}
          size="sm"
        >
          Новый заказ
        </Button>
      </Box>

      {/* Диалог ручного создания заказа */}
      <ManualOrderDialog 
        open={isManualOrderOpen} 
        onClose={() => setIsManualOrderOpen(false)} 
      />

      {/* Панель метрик системы */}
      <MetricsPanel />

      {/* Использование DeepSeek API */}
      <DeepSeekUsage />

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

      {/* График выручки */}
      <Card bg={bgColor} border="1px" borderColor={borderColor} mb={8}>
        <CardBody>
          <Text fontSize="xl" fontWeight="bold" mb={4}>
            Динамика выручки
          </Text>
          <RevenueChart />
        </CardBody>
      </Card>

      {/* Последняя активность и системное здоровье */}
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6} mb={8}>
        <RecentActivity />
        <SystemHealthCard />
      </SimpleGrid>

      {/* Таблица заказов */}
      <Card bg={bgColor} border="1px" borderColor={borderColor}>
        <CardBody>
          <HStack justifyContent="space-between" mb={4}>
            <Text fontSize="xl" fontWeight="bold">
              Последние заказы
            </Text>
            <Button
              size="sm"
              variant="outline"
              colorScheme="blue"
              onClick={() => setIsManualOrderOpen(true)}
            >
              <AddIcon mr={2} />
              Добавить заказ
            </Button>
          </HStack>
          <OrdersTable />
        </CardBody>
      </Card>
    </Box>
  );
};
