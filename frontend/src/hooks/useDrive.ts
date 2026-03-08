import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export interface DriveFile {
  id: string
  name: string
  mimeType: string
  size?: string
  modifiedTime: string
  webViewLink?: string
  parents?: string[]
}

export function useDriveFiles(folderId?: string, query?: string) {
  return useQuery<{ files: DriveFile[] }>({
    queryKey: ['drive', 'files', folderId, query],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (folderId) params.folder_id = folderId
      if (query) params.query = query
      const res = await api.get('/drive/files', { params })
      return res.data
    },
  })
}

export function useDriveFile(fileId: string | null) {
  return useQuery<DriveFile>({
    queryKey: ['drive', 'file', fileId],
    queryFn: async () => {
      const res = await api.get(`/drive/file/${fileId}`)
      return res.data
    },
    enabled: Boolean(fileId),
  })
}

export function useUploadFile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, folderId }: { file: File; folderId?: string }) => {
      const formData = new FormData()
      formData.append('file', file)
      const params: Record<string, string> = {}
      if (folderId) params.folder_id = folderId
      const res = await api.post('/drive/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        params,
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drive', 'files'] })
    },
  })
}
