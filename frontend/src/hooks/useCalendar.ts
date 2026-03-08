import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export interface CalendarEvent {
  id: string
  summary: string
  description?: string
  start: { dateTime?: string; date?: string; timeZone?: string }
  end: { dateTime?: string; date?: string; timeZone?: string }
  attendees?: Array<{ email: string; displayName?: string; responseStatus?: string }>
  htmlLink?: string
  status?: string
}

export interface EventCreatePayload {
  summary: string
  description?: string
  start: string
  end: string
  time_zone?: string
  attendees?: string[]
  calendar_id?: string
}

export interface EventUpdatePayload extends Partial<EventCreatePayload> {
  calendar_id?: string
}

export function useCalendarEvents(
  calendarId = 'primary',
  timeMin?: string,
  timeMax?: string
) {
  return useQuery<{ events: CalendarEvent[] }>({
    queryKey: ['calendar', 'events', calendarId, timeMin, timeMax],
    queryFn: async () => {
      const params: Record<string, string> = { calendar_id: calendarId }
      if (timeMin) params.time_min = timeMin
      if (timeMax) params.time_max = timeMax
      const res = await api.get('/calendar/events', { params })
      return res.data
    },
  })
}

export function useCreateEvent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: EventCreatePayload) =>
      api.post('/calendar/events', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export function useUpdateEvent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ eventId, payload }: { eventId: string; payload: EventUpdatePayload }) =>
      api.put(`/calendar/events/${eventId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export function useDeleteEvent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ eventId, calendarId = 'primary' }: { eventId: string; calendarId?: string }) =>
      api.delete(`/calendar/events/${eventId}`, { params: { calendar_id: calendarId } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}
