import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export interface GmailMessage {
  id: string
  threadId: string
  snippet: string
  subject: string
  from: string
  date: string
  labelIds: string[]
}

export interface GmailMessageDetail extends GmailMessage {
  to: string
  body: string
}

export interface SendEmailPayload {
  to: string
  subject: string
  body: string
  cc?: string
}

export interface ReplyEmailPayload {
  thread_id: string
  message_id: string
  body: string
  to: string
}

export function useGmailMessages(maxResults = 20, query?: string) {
  return useQuery<{ messages: GmailMessage[]; count: number }>({
    queryKey: ['gmail', 'messages', maxResults, query],
    queryFn: async () => {
      const params: Record<string, string | number> = { max_results: maxResults }
      if (query) params.query = query
      const res = await api.get('/gmail/messages', { params })
      return res.data
    },
  })
}

export function useGmailMessage(messageId: string | null) {
  return useQuery<GmailMessageDetail>({
    queryKey: ['gmail', 'message', messageId],
    queryFn: async () => {
      const res = await api.get(`/gmail/message/${messageId}`)
      return res.data
    },
    enabled: Boolean(messageId),
  })
}

export function useSendEmail() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: SendEmailPayload) => api.post('/gmail/send', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmail', 'messages'] })
    },
  })
}

export function useReplyEmail() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ReplyEmailPayload) => api.post('/gmail/reply', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmail', 'messages'] })
    },
  })
}
