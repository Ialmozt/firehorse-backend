import { useEffect, useState } from 'react'
import {
  Box, Stat, StatLabel, StatNumber, StatHelpText,
  Progress, HStack, Icon, Text, Badge, Skeleton,
  useToast, Heading
} from '@chakra-ui/react'
import { SettingsIcon, TimeIcon, StarIcon } from '@chakra-ui/icons'

interface Usage {
  tokensUsed: number
  tokensLimit: number
  estimatedCost: number
  dailyBudget: number
  resetIn: string
  lastUpdated: string
}

export function DeepSeekUsage() {
  const [usage, setUsage] = useState<Usage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    fetchUsage()
    const interval = setInterval(fetchUsage, 30000) // Обновление каждые 30 секунд
    return () => clearInterval(interval)
  }, [])

  async function fetchUsage() {
    try {
      const response = await fetch('http://localhost:8000/api/deepseek-usage')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      
      setUsage({
        tokensUsed: data.tokens_used || 0,
        tokensLimit: data.tokens_limit || 100000,
        estimatedCost: data.estimated_cost || 0,
        dailyBudget: data.daily_budget || 10,
        resetIn: formatTime(data.reset_seconds || 0),
        lastUpdated: new Date().toLocaleTimeString('ru-RU', { 
          hour: '2-digit', 
          minute: '2-digit',
          second: '2-digit'
        })
      })
      setLoading(false)
      setError(null)
    } catch (err) {
      console.error('DeepSeek usage fetch failed:', err)
      setError('Не удалось загрузить данные DeepSeek')
      setLoading(false)
      
      if (!usage) {
        toast({
          title: 'Ошибка загрузки DeepSeek',
          description: 'Проверьте подключение к бэкенду',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })
      }
    }
  }

  function formatTime(sec: number): string {
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    return `${h}ч ${m}м`
  }

  if (loading && !usage) {
    return (
      <Box bg="white" p={6} borderRadius="lg" shadow="md" mb={6}>
        <Heading size="md" mb={4}>
          <HStack><Icon as={SettingsIcon} /><span>DeepSeek API</span></HStack>
        </Heading>
        <Skeleton height="120px" borderRadius="md" />
      </Box>
    )
  }

  if (error && !usage) {
    return (
      <Box bg="white" p={6} borderRadius="lg" shadow="md" mb={6}>
        <Heading size="md" mb={4}>
          <HStack><Icon as={SettingsIcon} /><span>DeepSeek API</span></HStack>
        </Heading>
        <Text color="red.500">{error}</Text>
        <Text fontSize="sm" color="gray.500" mt={2}>
          Проверьте, запущен ли бэкенд на localhost:8000
        </Text>
      </Box>
    )
  }

  if (!usage) return null

  const usagePercent = (usage.tokensUsed / usage.tokensLimit) * 100
  const remaining = usage.tokensLimit - usage.tokensUsed
  const costPercent = (usage.estimatedCost / usage.dailyBudget) * 100

  return (
    <Box bg="white" p={6} borderRadius="lg" shadow="md" mb={6}>
      <HStack justifyContent="space-between" mb={4}>
        <Heading size="md">
          <HStack><Icon as={SettingsIcon} color="purple.500" /><span>DeepSeek API</span></HStack>
        </Heading>
        <Text fontSize="sm" color="gray.500">
          Обновлено: {usage.lastUpdated}
        </Text>
      </HStack>

      <Stat mb={4}>
        <StatLabel>
          <HStack><Icon as={TimeIcon} fontSize="sm" mr={1} /><span>Токены (сегодня)</span></HStack>
        </StatLabel>
        <StatNumber fontSize="lg">
          {usage.tokensUsed.toLocaleString()} / {usage.tokensLimit.toLocaleString()}
        </StatNumber>
        <Progress 
          value={usagePercent} 
          colorScheme={usagePercent > 90 ? 'red' : usagePercent > 70 ? 'yellow' : 'green'} 
          mt={2} 
          size="sm"
        />
        <StatHelpText fontSize="xs">
          Осталось: {remaining.toLocaleString()} ({(100 - usagePercent).toFixed(1)}%)
        </StatHelpText>
      </Stat>

      <Stat mb={4}>
        <StatLabel>
          <HStack><Icon as={StarIcon} fontSize="sm" mr={1} /><span>Стоимость</span></HStack>
        </StatLabel>
        <StatNumber fontSize="lg">
          ${usage.estimatedCost.toFixed(2)} / ${usage.dailyBudget.toFixed(2)}
        </StatNumber>
        <Progress 
          value={costPercent} 
          colorScheme={costPercent > 90 ? 'red' : costPercent > 70 ? 'yellow' : 'green'} 
          mt={2} 
          size="sm"
        />
        <StatHelpText fontSize="xs">
          {(usage.dailyBudget - usage.estimatedCost).toFixed(2)} осталось
        </StatHelpText>
      </Stat>

      <HStack justifyContent="space-between" mt={4}>
        <Badge colorScheme="purple" fontSize="xs">
          Сброс через {usage.resetIn}
        </Badge>
        <Text fontSize="xs" color="gray.500">
          Лимит: 100K токенов/день
        </Text>
      </HStack>
    </Box>
  )
}
