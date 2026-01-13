import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Text,
  Badge,
  VStack,
  HStack,
  Divider,
  Box,
  SimpleGrid,
  useColorModeValue,
  Skeleton,
  Alert,
  AlertIcon,
  Code,
  Tag,
  TagLabel,
} from '@chakra-ui/react';
import { useOrder } from '../hooks/useOrders';
import type { Order } from '../types';

interface OrderDetailsModalProps {
  orderId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

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

export const OrderDetailsModal: React.FC<OrderDetailsModalProps> = ({
  orderId,
  isOpen,
  onClose,
}) => {
  const { data, isLoading, error } = useOrder(orderId || '');
  const order = data?.data;

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'gray.200');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.400');

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const renderMetadata = (metadata: Record<string, any> | undefined) => {
    if (!metadata || Object.keys(metadata).length === 0) {
      return (
        <Text fontSize="sm" color={mutedTextColor} fontStyle="italic">
          Дополнительные данные отсутствуют
        </Text>
      );
    }

    return (
      <VStack align="stretch" spacing={2}>
        {Object.entries(metadata).map(([key, value]) => (
          <Box key={key}>
            <Text fontSize="sm" fontWeight="medium" color={textColor}>
              {key}:
            </Text>
            <Text fontSize="sm" color={mutedTextColor} ml={2}>
              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
            </Text>
          </Box>
        ))}
      </VStack>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg={bgColor}>
        <ModalHeader>
          <HStack spacing={3}>
            <Text>Детали заказа</Text>
            {order && (
              <Badge colorScheme={statusColors[order.status]}>
                {statusLabels[order.status]}
              </Badge>
            )}
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {isLoading ? (
            <VStack spacing={4} align="stretch">
              <Skeleton height="20px" />
              <Skeleton height="20px" />
              <Skeleton height="20px" />
              <Skeleton height="100px" />
            </VStack>
          ) : error ? (
            <Alert status="error">
              <AlertIcon />
              Ошибка загрузки данных заказа: {error.message}
            </Alert>
          ) : !order ? (
            <Alert status="warning">
              <AlertIcon />
              Заказ не найден
            </Alert>
          ) : (
            <VStack spacing={6} align="stretch">
              {/* Основная информация */}
              <Box>
                <Text fontSize="lg" fontWeight="bold" mb={3} color={textColor}>
                  Основная информация
                </Text>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={mutedTextColor}>
                      ID заказа
                    </Text>
                    <Code fontSize="xs" p={1} borderRadius="md" display="block" mt={1}>
                      {order.id}
                    </Code>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={mutedTextColor}>
                      ID источника
                    </Text>
                    <Text fontSize="md" fontWeight="medium" color={textColor}>
                      {order.source_id}
                    </Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={mutedTextColor}>
                      Тема
                    </Text>
                    <Text fontSize="md" fontWeight="medium" color={textColor}>
                      {order.topic}
                    </Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={mutedTextColor}>
                      Клиент
                    </Text>
                    <Text fontSize="md" fontWeight="medium" color={textColor}>
                      {order.customer}
                    </Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={mutedTextColor}>
                      Сумма
                    </Text>
                    <Text fontSize="xl" fontWeight="bold" color="green.500">
                      ${order.amount.toFixed(2)}
                    </Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={mutedTextColor}>
                      Статус
                    </Text>
                    <Badge colorScheme={statusColors[order.status]} fontSize="md" p={1}>
                      {statusLabels[order.status]}
                    </Badge>
                  </Box>
                </SimpleGrid>
              </Box>

              <Divider />

              {/* Временные метки */}
              <Box>
                <Text fontSize="lg" fontWeight="bold" mb={3} color={textColor}>
                  Временные метки
                </Text>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={mutedTextColor}>
                      Создан
                    </Text>
                    <Text fontSize="md" color={textColor}>
                      {formatDate(order.created_at)}
                    </Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={mutedTextColor}>
                      Обновлён
                    </Text>
                    <Text fontSize="md" color={textColor}>
                      {formatDate(order.updated_at)}
                    </Text>
                  </Box>
                </SimpleGrid>
              </Box>

              <Divider />

              {/* Дополнительные данные (metadata) */}
              <Box>
                <Text fontSize="lg" fontWeight="bold" mb={3} color={textColor}>
                  Дополнительные данные
                </Text>
                {renderMetadata(order.metadata)}
              </Box>

              {/* Тэги для быстрой навигации */}
              {order.metadata && (
                <>
                  <Divider />
                  <Box>
                    <Text fontSize="lg" fontWeight="bold" mb={3} color={textColor}>
                      Ключевые теги
                    </Text>
                    <HStack spacing={2} flexWrap="wrap">
                      {Object.keys(order.metadata).map((key) => (
                        <Tag key={key} colorScheme="blue" size="md">
                          <TagLabel>{key}</TagLabel>
                        </Tag>
                      ))}
                    </HStack>
                  </Box>
                </>
              )}
            </VStack>
          )}
        </ModalBody>

        <ModalFooter>
          <Button colorScheme="blue" mr={3} onClick={onClose}>
            Закрыть
          </Button>
          {order && (
            <Button variant="outline" onClick={() => window.alert('Функция редактирования в разработке')}>
              Редактировать
            </Button>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
