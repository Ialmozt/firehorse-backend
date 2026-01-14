import { useState } from 'react'
import {
  Button, useToast, Modal, ModalOverlay, ModalContent,
  ModalHeader, ModalBody, ModalFooter, Input, FormControl,
  FormLabel, Textarea, VStack, HStack, Badge, Text,
  useDisclosure, Box, Spinner
} from '@chakra-ui/react'
import { AddIcon, CheckIcon, WarningIcon } from '@chakra-ui/icons'

export function TestOrderButton() {
  const { isOpen, onOpen, onClose } = useDisclosure()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const toast = useToast()

  const [formData, setFormData] = useState({
    sourceId: `test-${Date.now()}`,
    topic: 'Тестовый заказ для проверки системы',
    description: 'Это тестовый заказ, созданный через интерфейс'
  })

  async function createTestOrder() {
    setLoading(true)
    setResult(null)

    try {
      const response = await fetch('http://localhost:8000/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: formData.topic,
          description: formData.description,
          source_id: formData.sourceId
        })
      })

      const data = await response.json()

      if (data.success) {
        setResult({
          success: true,
          orderId: data.data.id,
          status: data.data.status,
          message: 'Заказ успешно создан!'
        })

        toast({
          title: 'Заказ создан',
          description: `ID: ${data.data.id}`,
          status: 'success',
          duration: 5000,
          isClosable: true,
        })
      } else {
        setResult({
          success: false,
          error: data.error?.message || 'Неизвестная ошибка',
          message: 'Не удалось создать заказ'
        })

        toast({
          title: 'Ошибка',
          description: data.error?.message || 'Не удалось создать заказ',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })
      }
    } catch (error) {
      setResult({
        success: false,
        error: error instanceof Error ? error.message : 'Network error',
        message: 'Ошибка сети'
      })

      toast({
        title: 'Ошибка сети',
        description: 'Проверьте подключение к бэкенду',
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    createTestOrder()
  }

  return (
    <>
      <Button
        leftIcon={<AddIcon />}
        colorScheme="blue"
        variant="outline"
        onClick={onOpen}
        size="sm"
      >
        Тестовый заказ
      </Button>

      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <form onSubmit={handleSubmit}>
            <ModalHeader>Создать тестовый заказ</ModalHeader>
            <ModalBody>
              <VStack spacing={4}>
                <FormControl isRequired>
                  <FormLabel>Source ID</FormLabel>
                  <Input
                    value={formData.sourceId}
                    onChange={(e) => setFormData({...formData, sourceId: e.target.value})}
                    placeholder="kwork_12345"
                  />
                </FormControl>

                <FormControl isRequired>
                  <FormLabel>Тема заказа</FormLabel>
                  <Input
                    value={formData.topic}
                    onChange={(e) => setFormData({...formData, topic: e.target.value})}
                    placeholder="Напишите статью о..."
                  />
                </FormControl>

                <FormControl>
                  <FormLabel>Описание</FormLabel>
                  <Textarea
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    placeholder="Детальное описание заказа..."
                    rows={3}
                  />
                </FormControl>

                {result && (
                  <Box
                    p={4}
                    borderRadius="md"
                    bg={result.success ? 'green.50' : 'red.50'}
                    borderWidth="1px"
                    borderColor={result.success ? 'green.200' : 'red.200'}
                    width="100%"
                  >
                    <HStack spacing={2} mb={2}>
                      {result.success ? (
                        <CheckIcon color="green.500" />
                      ) : (
                        <WarningIcon color="red.500" />
                      )}
                      <Text fontWeight="bold">
                        {result.success ? 'Успешно!' : 'Ошибка!'}
                      </Text>
                    </HStack>
                    
                    <Text fontSize="sm" mb={2}>
                      {result.message}
                    </Text>

                    {result.success && (
                      <HStack spacing={2}>
                        <Badge colorScheme="green">ID: {result.orderId}</Badge>
                        <Badge colorScheme="blue">Status: {result.status}</Badge>
                      </HStack>
                    )}

                    {!result.success && result.error && (
                      <Text fontSize="sm" color="red.600">
                        {result.error}
                      </Text>
                    )}
                  </Box>
                )}
              </VStack>
            </ModalBody>

            <ModalFooter>
              <HStack spacing={3}>
                <Button variant="ghost" onClick={onClose}>
                  Отмена
                </Button>
                <Button
                  type="submit"
                  colorScheme="blue"
                  isLoading={loading}
                  leftIcon={loading ? <Spinner size="sm" /> : <AddIcon />}
                >
                  Создать заказ
                </Button>
              </HStack>
            </ModalFooter>
          </form>
        </ModalContent>
      </Modal>
    </>
  )
}
