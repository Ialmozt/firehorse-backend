import React, { useState } from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Badge,
  Text,
  HStack,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useColorModeValue,
  Skeleton,
  Box,
  Select,
  Input,
  InputGroup,
  InputLeftElement,
} from '@chakra-ui/react';
import {
  ChevronDownIcon,
  SearchIcon,
  ViewIcon,
  EditIcon,
  DeleteIcon,
  RepeatIcon,
} from '@chakra-ui/icons';
import { useOrders } from '../hooks/useOrders';
import type { Order } from '../types';

const statusColors: Record<string, string> = {
  queued: 'blue',
  processing: 'yellow',
  completed: 'green',
  failed: 'red',
};

const statusLabels: Record<string, string> = {
  queued: 'В очереди',
  processing: 'В обработке',
  completed: 'Завершён',
  failed: 'Ошибка',
};

export const OrdersTable: React.FC = () => {
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data, isLoading, error, refetch } = useOrders(page, limit);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const orders = data?.data?.items || [];
  const pagination = data?.data?.pagination || { total: 0, page: 1, limit: 10, total_pages: 1 };

  const filteredOrders = orders.filter((order: Order) => {
    const matchesSearch = search === '' || 
      order.source_id.toLowerCase().includes(search.toLowerCase()) ||
      order.topic.toLowerCase().includes(search.toLowerCase()) ||
      order.customer.toLowerCase().includes(search.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const handleRefresh = () => {
    refetch();
  };

  if (isLoading) {
    return (
      <Box>
        <Skeleton height="40px" mb={4} />
        <Skeleton height="300px" />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={4} textAlign="center">
        <Text color="red.500">Ошибка загрузки заказов: {error.message}</Text>
        <IconButton
          mt={2}
          aria-label="Повторить"
          icon={<RepeatIcon />}
          onClick={handleRefresh}
        />
      </Box>
    );
  }

  return (
    <Box>
      {/* Фильтры и поиск */}
      <HStack mb={4} spacing={4} flexWrap="wrap">
        <InputGroup maxW="300px">
          <InputLeftElement pointerEvents="none">
            <SearchIcon color="gray.400" />
          </InputLeftElement>
          <Input
            placeholder="Поиск заказов..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </InputGroup>

        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          maxW="200px"
        >
          <option value="all">Все статусы</option>
          <option value="queued">В очереди</option>
          <option value="processing">В обработке</option>
          <option value="completed">Завершён</option>
          <option value="failed">Ошибка</option>
        </Select>

        <IconButton
          aria-label="Обновить"
          icon={<RepeatIcon />}
          onClick={handleRefresh}
          isLoading={isLoading}
        />

        <Text fontSize="sm" color="gray.600" ml="auto">
          Всего: {pagination.total} заказов
        </Text>
      </HStack>

      {/* Таблица */}
      <TableContainer
        border="1px"
        borderColor={borderColor}
        borderRadius="lg"
        bg={bgColor}
      >
        <Table variant="simple">
          <Thead>
            <Tr>
              <Th>ID</Th>
              <Th>Источник</Th>
              <Th>Тема</Th>
              <Th>Статус</Th>
              <Th>Клиент</Th>
              <Th>Сумма</Th>
              <Th>Создан</Th>
              <Th>Действия</Th>
            </Tr>
          </Thead>
          <Tbody>
            {filteredOrders.length === 0 ? (
              <Tr>
                <Td colSpan={8} textAlign="center" py={8}>
                  <Text color="gray.500">Заказы не найдены</Text>
                </Td>
              </Tr>
            ) : (
              filteredOrders.map((order: Order) => (
                <Tr key={order.id} _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }}>
                  <Td>
                    <Text fontFamily="mono" fontSize="xs">
                      {order.id.slice(0, 8)}...
                    </Text>
                  </Td>
                  <Td>
                    <Text fontSize="sm" fontWeight="medium">
                      {order.source_id}
                    </Text>
                  </Td>
                  <Td>
                    <Text fontSize="sm">{order.topic}</Text>
                  </Td>
                  <Td>
                    <Badge colorScheme={statusColors[order.status]}>
                      {statusLabels[order.status]}
                    </Badge>
                  </Td>
                  <Td>
                    <Text fontSize="sm">{order.customer}</Text>
                  </Td>
                  <Td>
                    <Text fontSize="sm" fontWeight="bold">
                      ${order.amount}
                    </Text>
                  </Td>
                  <Td>
                    <Text fontSize="xs">
                      {new Date(order.created_at).toLocaleDateString()}
                    </Text>
                    <Text fontSize="xs" color="gray.500">
                      {new Date(order.created_at).toLocaleTimeString()}
                    </Text>
                  </Td>
                  <Td>
                    <Menu>
                      <MenuButton
                        as={IconButton}
                        aria-label="Действия"
                        icon={<ChevronDownIcon />}
                        size="sm"
                        variant="ghost"
                      />
                      <MenuList>
                        <MenuItem icon={<ViewIcon />}>Просмотр</MenuItem>
                        <MenuItem icon={<EditIcon />}>Редактировать</MenuItem>
                        <MenuItem icon={<DeleteIcon />} color="red.500">
                          Удалить
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  </Td>
                </Tr>
              ))
            )}
          </Tbody>
        </Table>
      </TableContainer>

      {/* Пагинация */}
      {pagination.total_pages > 1 && (
        <HStack mt={4} justifyContent="space-between">
          <Text fontSize="sm" color="gray.600">
            Страница {pagination.page} из {pagination.total_pages}
          </Text>
          <HStack>
            <Select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              size="sm"
              maxW="100px"
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </Select>
            <HStack>
              <IconButton
                aria-label="Предыдущая страница"
                icon={<ChevronDownIcon transform="rotate(90deg)" />}
                size="sm"
                isDisabled={pagination.page === 1}
                onClick={() => setPage(pagination.page - 1)}
              />
              <IconButton
                aria-label="Следующая страница"
                icon={<ChevronDownIcon transform="rotate(-90deg)" />}
                size="sm"
                isDisabled={pagination.page === pagination.total_pages}
                onClick={() => setPage(pagination.page + 1)}
              />
            </HStack>
          </HStack>
        </HStack>
      )}
    </Box>
  );
};
