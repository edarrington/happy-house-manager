'use client'

import { useState, useRef } from 'react'
import Header from '@/components/Header'
import { useDriveFiles, useUploadFile } from '@/hooks/useDrive'
import { FolderOpen, Upload, ExternalLink, File, RefreshCw } from 'lucide-react'

function formatSize(bytes?: string): string {
  if (!bytes) return ''
  const n = parseInt(bytes, 10)
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export default function DrivePage() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, isLoading, refetch } = useDriveFiles(undefined, debouncedQuery || undefined)
  const uploadFile = useUploadFile()

  const handleSearch = (v: string) => {
    setQuery(v)
    // Simple debounce via setTimeout
    clearTimeout((window as unknown as { _driveSearchTimeout?: ReturnType<typeof setTimeout> })._driveSearchTimeout)
    ;(window as unknown as { _driveSearchTimeout?: ReturnType<typeof setTimeout> })._driveSearchTimeout = setTimeout(() => setDebouncedQuery(v), 400)
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    await uploadFile.mutateAsync({ file })
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="flex flex-col flex-1">
      <Header title="Google Drive" subtitle="Browse and upload files" />
      <div className="p-6">
        {/* Toolbar */}
        <div className="flex gap-3 mb-6">
          <input
            type="text"
            className="input max-w-xs"
            placeholder="Search files..."
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
          />
          <button onClick={() => refetch()} className="btn-secondary">
            <RefreshCw size={16} />
          </button>
          <button onClick={() => fileInputRef.current?.click()} className="btn-primary">
            <Upload size={16} /> Upload
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleUpload}
          />
        </div>

        {/* File grid */}
        {isLoading ? (
          <p className="text-gray-400">Loading files...</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {data?.files.map((f) => (
              <div key={f.id} className="card p-4 flex flex-col gap-2 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <File size={20} className="text-blue-600" />
                  </div>
                  {f.webViewLink && (
                    <a
                      href={f.webViewLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-400 hover:text-blue-600"
                    >
                      <ExternalLink size={16} />
                    </a>
                  )}
                </div>
                <p className="text-sm font-medium text-gray-900 truncate" title={f.name}>{f.name}</p>
                <p className="text-xs text-gray-400">{formatSize(f.size)}</p>
                <p className="text-xs text-gray-400">{new Date(f.modifiedTime).toLocaleDateString()}</p>
              </div>
            ))}
            {!data?.files.length && (
              <p className="text-gray-400 col-span-full">No files found.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
