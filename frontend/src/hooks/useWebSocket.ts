/**
 * WebSocket Hook for Real-Time Job Updates (Epic 10)
 *
 * Features:
 * - Automatic connection management
 * - Exponential backoff reconnection (1s, 2s, 4s, 8s, 16s, max 30s)
 * - Heartbeat/keep-alive support
 * - Type-safe message handling
 * - Connection status tracking
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { supabase } from '@/lib/supabase'

// ============================================================================
// Types
// ============================================================================

export type WebSocketMessageType =
  | 'connected'
  | 'heartbeat'
  | 'job_progress'
  | 'job_completed'
  | 'job_failed'
  | 'character_status_update'

export interface WebSocketMessage {
  type: WebSocketMessageType
  timestamp: string
}

export interface JobProgressMessage extends WebSocketMessage {
  type: 'job_progress'
  job_id: string
  status: string
  stage: string | null
  progress_percentage: number
  estimated_completion: string | null
  time_remaining_seconds: number | null
}

export interface JobCompletedMessage extends WebSocketMessage {
  type: 'job_completed'
  job_id: string
  sub_chapter_id: string
  word_count: number
  version_id: string
  version_number: number
  notification_type: string
  title: string
  message: string
  action_url: string
  action_label: string
}

export interface JobFailedMessage extends WebSocketMessage {
  type: 'job_failed'
  job_id: string
  error_message: string
  error_type: string | null
  can_retry: boolean
  notification_type: string
  title: string
  message: string
  action_url: string | null
  action_label: string
}

export interface CharacterStatusMessage extends WebSocketMessage {
  type: 'character_status_update'
  character_id: string
  status: string
  collection_name: string | null
  embedding_count: number | null
  can_generate: boolean
}

export interface ConnectedMessage extends WebSocketMessage {
  type: 'connected'
  user_id: string
  message: string
}

export interface HeartbeatMessage extends WebSocketMessage {
  type: 'heartbeat'
}

export type AnyWebSocketMessage =
  | JobProgressMessage
  | JobCompletedMessage
  | JobFailedMessage
  | CharacterStatusMessage
  | ConnectedMessage
  | HeartbeatMessage

export type MessageHandler = (message: AnyWebSocketMessage) => void

export interface UseWebSocketOptions {
  /**
   * Whether to automatically connect on mount
   * @default true
   */
  autoConnect?: boolean

  /**
   * Whether to automatically reconnect on disconnect
   * @default true
   */
  autoReconnect?: boolean

  /**
   * Maximum reconnection delay in seconds
   * @default 30
   */
  maxReconnectDelay?: number

  /**
   * Callback when connection is established
   */
  onConnect?: () => void

  /**
   * Callback when connection is closed
   */
  onDisconnect?: () => void

  /**
   * Callback for connection errors
   */
  onError?: (error: Event) => void
}

export interface UseWebSocketReturn {
  /**
   * Current connection status
   */
  status: 'connecting' | 'connected' | 'disconnected' | 'error'

  /**
   * Whether currently connected
   */
  isConnected: boolean

  /**
   * Manually connect to WebSocket
   */
  connect: () => void

  /**
   * Manually disconnect from WebSocket
   */
  disconnect: () => void

  /**
   * Subscribe to specific message type
   */
  subscribe: <T extends AnyWebSocketMessage>(
    type: WebSocketMessageType,
    handler: (message: T) => void
  ) => () => void

  /**
   * Subscribe to all messages
   */
  subscribeAll: (handler: MessageHandler) => () => void

  /**
   * Last error that occurred
   */
  error: string | null
}

// ============================================================================
// Hook
// ============================================================================

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    autoConnect = true,
    autoReconnect = true,
    maxReconnectDelay = 30,
    onConnect,
    onDisconnect,
    onError,
  } = options

  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>(
    'disconnected'
  )
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const handlersRef = useRef<Map<WebSocketMessageType, Set<MessageHandler>>>(new Map())
  const allHandlersRef = useRef<Set<MessageHandler>>(new Set())
  const shouldReconnectRef = useRef(autoReconnect)

  /**
   * Get WebSocket URL with auth token
   */
  const getWebSocketUrl = useCallback(async (): Promise<string | null> => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session?.access_token) {
        console.warn('No access token available for WebSocket connection')
        return null
      }

      const wsBaseUrl =
        import.meta.env.VITE_API_BASE_URL?.replace('http://', 'ws://').replace(
          'https://',
          'wss://'
        ) || ''

      return `${wsBaseUrl}/api/generation-jobs/ws?token=${session.access_token}`
    } catch (error) {
      console.error('Error getting WebSocket URL:', error)
      return null
    }
  }, [])

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(async () => {
    // Don't connect if already connected/connecting
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) {
      return
    }

    setStatus('connecting')
    setError(null)

    try {
      const url = await getWebSocketUrl()
      if (!url) {
        setStatus('error')
        setError('Failed to get WebSocket URL')
        return
      }

      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setStatus('connected')
        setError(null)
        reconnectAttemptsRef.current = 0
        onConnect?.()
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setStatus('disconnected')
        wsRef.current = null
        onDisconnect?.()

        // Attempt reconnection if enabled
        if (shouldReconnectRef.current && autoReconnect) {
          scheduleReconnect()
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setStatus('error')
        setError('WebSocket connection error')
        onError?.(event)
      }

      ws.onmessage = (event) => {
        try {
          const message: AnyWebSocketMessage = JSON.parse(event.data)

          // Call all message handlers
          allHandlersRef.current.forEach((handler) => {
            try {
              handler(message)
            } catch (error) {
              console.error('Error in message handler:', error)
            }
          })

          // Call type-specific handlers
          const typeHandlers = handlersRef.current.get(message.type)
          if (typeHandlers) {
            typeHandlers.forEach((handler) => {
              try {
                handler(message)
              } catch (error) {
                console.error(`Error in ${message.type} handler:`, error)
              }
            })
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      setStatus('error')
      setError('Failed to create WebSocket connection')
    }
  }, [getWebSocketUrl, autoReconnect, onConnect, onDisconnect, onError])

  /**
   * Schedule reconnection with exponential backoff
   */
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    // Calculate delay: 1s, 2s, 4s, 8s, 16s, max 30s
    const delay = Math.min(
      Math.pow(2, reconnectAttemptsRef.current) * 1000,
      maxReconnectDelay * 1000
    )

    console.log(
      `Scheduling reconnect attempt ${reconnectAttemptsRef.current + 1} in ${delay / 1000}s`
    )

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptsRef.current++
      connect()
    }, delay)
  }, [connect, maxReconnectDelay])

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setStatus('disconnected')
  }, [])

  /**
   * Subscribe to specific message type
   */
  const subscribe = useCallback(
    <T extends AnyWebSocketMessage>(
      type: WebSocketMessageType,
      handler: (message: T) => void
    ): (() => void) => {
      if (!handlersRef.current.has(type)) {
        handlersRef.current.set(type, new Set())
      }

      const handlers = handlersRef.current.get(type)!
      handlers.add(handler as MessageHandler)

      // Return unsubscribe function
      return () => {
        handlers.delete(handler as MessageHandler)
        if (handlers.size === 0) {
          handlersRef.current.delete(type)
        }
      }
    },
    []
  )

  /**
   * Subscribe to all messages
   */
  const subscribeAll = useCallback((handler: MessageHandler): (() => void) => {
    allHandlersRef.current.add(handler)

    // Return unsubscribe function
    return () => {
      allHandlersRef.current.delete(handler)
    }
  }, [])

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    // Cleanup on unmount
    return () => {
      shouldReconnectRef.current = false
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]) // Only re-run if autoConnect changes, not connect/disconnect functions

  return {
    status,
    isConnected: status === 'connected',
    connect,
    disconnect,
    subscribe,
    subscribeAll,
    error,
  }
}
