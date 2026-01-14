import { useEffect, useState } from 'react'
import {
  Box,
  Grid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Progress,
  Badge,
  Heading,
  HStack,
  Icon,
  Skeleton,
  Text,
  useToast,
} from '@chakra-ui/react'
import { CheckCircleIcon, TimeIcon, SettingsIcon, WarningIcon, NotAllowedIcon } from '@chakra-ui/icons'

interface Metrics {
  apiHealth: 'healthy' | 'degraded' | 'down'
  uptime: string
  avgResponseTime: number
  requestRate: number
  errorRate: number
  cpuUsage: number
  memoryUsageMB: number
  memoryTotalMB: number
  activeWorkers: number
  totalWorkers: number
  databaseStatus: 'connected' | 'disconnected'
  lastUpdated: string
}

export function MetricsPanel() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 10000) // Обновление каждые 10 секунд
    return () => clearInterval(interval)
  }, [])

  async function fetchMetrics() {
    try {
      const response = await fetch('http://localhost:8000/api/system-metrics')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      
      setMetrics({
        apiHealth: data.status === 'healthy' ? 'healthy' : 'degraded',
        uptime: formatUptime(data.uptime_seconds || 0),
        avgResponseTime: data.avg_response_time_ms || 0,
        requestRate: data.requests_per_minute || 0,
        errorRate: data.error_rate_percent || 0,
        cpuUsage: data.cpu_percent || 0,
        memoryUsageMB: data.memory_mb || 0,
        memoryTotalMB: data.memory_total_mb || 2048,
        activeWorkers: data.active_workers || 1,
        totalWorkers: data.total_workers || 5,
        databaseStatus: data.database_status || 'connected',
        lastUpdated: new Date().toLocaleTimeString('ru-RU', { 
          hour: '2-digit', 
          minute: '2-digit',
          second: '2-digit'
        })
      })
      setLoading(false)
      setError(null)
    } catch (error) {
      console.error('Metrics fetch failed:', error)
      setError('Не удалось загрузить метрики')
      setLoading(false)
      
      // Показываем toast только при первой ошибке
      if (!metrics) {
        toast({
          title: 'Ошибка загрузки метрик',
          description: 'Проверьте подключение к бэкенду',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })
      }
    }
  }

  function formatUptime(seconds: number): string {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    return `${h}ч ${m}м ${s}с`
  }

  if (loading && !metrics) {
    return (
      <Box bg="white" p={6} borderRadius="lg" shadow="md" mb={6}>
        <Heading size="md" mb={4}>
          <HStack><Icon as={TimeIcon} /><span>Системные метрики</span></HStack>
        </Heading>
        <Grid templateColumns="repeat(auto-fit, minmax(200px, 1fr))" gap={4}>
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} height="80px" borderRadius="md" />
          ))}
        </Grid>
      </Box>
    )
  }

  if (error && !metrics) {
    return (
      <Box bg="white" p={6} borderRadius="lg" shadow="md" mb={6}>
        <Heading size="md" mb={4}>
          <HStack><Icon as={WarningIcon} /><span>Системные метрики</span></HStack>
        </Heading>
        <Text color="red.500">{error}</Text>
        <Text fontSize="sm" color="gray.500" mt={2}>
          Проверьте, запущен ли бэкенд на localhost:8000
        </Text>
      </Box>
    )
  }

  if (!metrics) return null

  return (
    <Box bg="white" p={6} borderRadius="lg" shadow="md" mb={6}>
      <HStack justifyContent="space-between" mb={4}>
        <Heading size="md">
          <HStack><Icon as={SettingsIcon} color="blue.500" /><span>Системные метрики</span></HStack>
        </Heading>
        <Text fontSize="sm" color="gray.500">
          Обновлено: {metrics.lastUpdated}
        </Text>
      </HStack>

      <Grid templateColumns="repeat(auto-fit, minmax(200px, 1fr))" gap={4}>
        <Stat p={3} bg="gray.50" borderRadius="md">
          <StatLabel>
            <HStack><Icon as={CheckCircleIcon} fontSize="sm" /><span>API Health</span></HStack>
          </StatLabel>
          <Badge 
            colorScheme={metrics.apiHealth === 'healthy' ? 'green' : metrics.apiHealth === 'degraded' ? 'yellow' : 'red'}
            fontSize="sm"
            mt={1}
          >
            {metrics.apiHealth === 'healthy' ? 'ЗДОРОВ' : metrics.apiHealth === 'degraded' ? 'ДЕГРАДАЦИЯ' : 'НЕДОСТУПЕН'}
          </Badge>
          <StatHelpText fontSize="xs">⏱ {metrics.uptime}</StatHelpText>
        </Stat>

        <Stat p={3} bg="gray.50" borderRadius="md">
          <StatLabel>
            <HStack><Icon as={TimeIcon} fontSize="sm" /><span>Response Time</span></HStack>
          </StatLabel>
          <StatNumber fontSize="lg" color={metrics.avgResponseTime > 500 ? 'red.500' : 'green.500'}>
            {metrics.avgResponseTime}ms
          </StatNumber>
          <StatHelpText fontSize="xs">{metrics.requestRate} req/min</StatHelpText>
        </Stat>

        <Stat p={3} bg="gray.50" borderRadius="md">
          <StatLabel>
            <HStack><Icon as={WarningIcon} fontSize="sm" /><span>Error Rate</span></HStack>
          </StatLabel>
          <StatNumber fontSize="lg" color={metrics.errorRate > 5 ? 'red.500' : metrics.errorRate > 2 ? 'yellow.500' : 'green.500'}>
            {metrics.errorRate.toFixed(2)}%
          </StatNumber>
          <Progress 
            value={metrics.errorRate} 
            max={10}
            size="sm" 
            colorScheme={metrics.errorRate > 5 ? 'red' : metrics.errorRate > 2 ? 'yellow' : 'green'}
            mt={2} 
          />
        </Stat>

        <Stat p={3} bg="gray.50" borderRadius="md">
          <StatLabel>
            <HStack><Icon as={SettingsIcon} fontSize="sm" /><span>CPU Usage</span></HStack>
          </StatLabel>
          <StatNumber fontSize="lg">{metrics.cpuUsage.toFixed(1)}%</StatNumber>
          <Progress 
            value={metrics.cpuUsage} 
            size="sm" 
            colorScheme={metrics.cpuUsage > 80 ? 'red' : metrics.cpuUsage > 60 ? 'yellow' : 'blue'}
            mt={2} 
          />
        </Stat>

        <Stat p={3} bg="gray.50" borderRadius="md">
          <StatLabel>
            <HStack><Icon as={SettingsIcon} fontSize="sm" /><span>Memory</span></HStack>
          </StatLabel>
          <StatNumber fontSize="sm">
            {metrics.memoryUsageMB}MB / {metrics.memoryTotalMB}MB
          </StatNumber>
          <Progress 
            value={(metrics.memoryUsageMB / metrics.memoryTotalMB) * 100} 
            size="sm" 
            colorScheme={metrics.memoryUsageMB / metrics.memoryTotalMB > 0.8 ? 'red' : 'purple'}
            mt={2} 
          />
          <StatHelpText fontSize="xs">
            {((metrics.memoryUsageMB / metrics.memoryTotalMB) * 100).toFixed(1)}% used
          </StatHelpText>
        </Stat>

        <Stat p={3} bg="gray.50" borderRadius="md">
          <StatLabel>
            <HStack><Icon as={NotAllowedIcon} fontSize="sm" /><span>Database</span></HStack>
          </StatLabel>
          <Badge 
            colorScheme={metrics.databaseStatus === 'connected' ? 'green' : 'red'}
            fontSize="sm"
            mt={1}
          >
            {metrics.databaseStatus === 'connected' ? 'ПОДКЛЮЧЕНА' : 'ОТКЛЮЧЕНА'}
          </Badge>
          <StatHelpText fontSize="xs">
            Workers: {metrics.activeWorkers}/{metrics.totalWorkers}
          </StatHelpText>
        </Stat>
      </Grid>
    </Box>
  )
}
