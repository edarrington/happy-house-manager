import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export interface TodoistProject {
  id: string
  name: string
  color: string
  order: number
  is_shared: boolean
  is_favorite: boolean
}

export interface TodoistTask {
  id: string
  content: string
  description: string
  project_id: string
  priority: number
  due?: { date: string; string: string; datetime?: string }
  is_completed: boolean
  labels: string[]
  created_at: string
}

export interface TaskCreatePayload {
  content: string
  project_id?: string
  due_string?: string
  priority?: number
  description?: string
}

export interface TaskUpdatePayload {
  content?: string
  due_string?: string
  priority?: number
  description?: string
}

export function useTodoistProjects() {
  return useQuery<{ projects: TodoistProject[] }>({
    queryKey: ['todoist', 'projects'],
    queryFn: async () => {
      const res = await api.get('/todoist/projects')
      return res.data
    },
  })
}

export function useTodoistTasks(projectId?: string, filterStr?: string) {
  return useQuery<{ tasks: TodoistTask[] }>({
    queryKey: ['todoist', 'tasks', projectId, filterStr],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (projectId) params.project_id = projectId
      if (filterStr) params.filter_str = filterStr
      const res = await api.get('/todoist/tasks', { params })
      return res.data
    },
  })
}

export function useCreateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: TaskCreatePayload) => api.post('/todoist/tasks', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['todoist', 'tasks'] })
    },
  })
}

export function useUpdateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: TaskUpdatePayload }) =>
      api.put(`/todoist/tasks/${taskId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['todoist', 'tasks'] })
    },
  })
}

export function useDeleteTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => api.delete(`/todoist/tasks/${taskId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['todoist', 'tasks'] })
    },
  })
}
