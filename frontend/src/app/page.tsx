'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated, getStoredUser, type User } from '@/lib/auth'
import { useGmailMessages } from '@/hooks/useGmail'
import { useCalendarEvents } from '@/hooks/useCalendar'
import { useDriveFiles } from '@/hooks/useDrive'
import { useTodoistTasks } from '@/hooks/useTodoist'
import Header from '@/components/Header'
import { Mail, Calendar, FolderOpen, CheckSquare, AlertCircle } from 'lucide-react'
import { redirectToGoogleLogin } from '@/lib/auth'

function SummaryCard({
  title,
  count,
  icon: Icon,
  color,
  href,
}: {
  title: string
  count: number | undefined
  icon: React.ElementType
  color: string
  href: string
}) {
  return (
    <a
      href={href}
      className="card p-6 flex items-center gap-4 hover:shadow-md transition-shadow"
    >
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon size={24} className="text-white" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-900">
          {count !== undefined ? count : '—'}
        </p>
      </div>
    </a>
  )
}

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    if (!isAuthenticated()) {
      return
    }
    setUser(getStoredUser())
  }, [router])

  const { data: gmailData } = useGmailMessages(5)
  const { data: calendarData } = useCalendarEvents()
  const { data: driveData } = useDriveFiles()
  const { data: todoistData } = useTodoistTasks()

  if (!mounted) return null

  if (!isAuthenticated()) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 p-8">
        <div className="card p-8 max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Happy House</h1>
          <p className="text-gray-500 mb-6">
            Sign in with your Google account to access the family dashboard.
          </p>
          <button
            onClick={redirectToGoogleLogin}
            className="btn-primary w-full justify-center"
          >
            Sign in with Google
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1">
      <Header
        title="Dashboard"
        subtitle={`Welcome back, ${user?.name?.split(' ')[0] ?? 'there'}!`}
      />

      <div className="p-6 space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryCard
            title="Inbox Messages"
            count={gmailData?.count}
            icon={Mail}
            color="bg-red-500"
            href="/gmail"
          />
          <SummaryCard
            title="Upcoming Events"
            count={calendarData?.events?.length}
            icon={Calendar}
            color="bg-blue-500"
            href="/calendar"
          />
          <SummaryCard
            title="Drive Files"
            count={driveData?.files?.length}
            icon={FolderOpen}
            color="bg-yellow-500"
            href="/drive"
          />
          <SummaryCard
            title="Open Tasks"
            count={todoistData?.tasks?.length}
            icon={CheckSquare}
            color="bg-green-500"
            href="/tasks"
          />
        </div>

        {/* Recent activity rows */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent emails */}
          <div className="card">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900">Recent Emails</h3>
            </div>
            <ul className="divide-y divide-gray-100">
              {gmailData?.messages?.slice(0, 5).map((msg) => (
                <li key={msg.id} className="px-6 py-3 hover:bg-gray-50">
                  <p className="text-sm font-medium text-gray-900 truncate">{msg.subject}</p>
                  <p className="text-xs text-gray-500 truncate">{msg.from}</p>
                </li>
              ))}
              {!gmailData?.messages?.length && (
                <li className="px-6 py-4 text-sm text-gray-400">No recent emails</li>
              )}
            </ul>
          </div>

          {/* Upcoming events */}
          <div className="card">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900">Upcoming Events</h3>
            </div>
            <ul className="divide-y divide-gray-100">
              {calendarData?.events?.slice(0, 5).map((evt) => (
                <li key={evt.id} className="px-6 py-3 hover:bg-gray-50">
                  <p className="text-sm font-medium text-gray-900">{evt.summary}</p>
                  <p className="text-xs text-gray-500">
                    {evt.start.dateTime
                      ? new Date(evt.start.dateTime).toLocaleString()
                      : evt.start.date}
                  </p>
                </li>
              ))}
              {!calendarData?.events?.length && (
                <li className="px-6 py-4 text-sm text-gray-400">No upcoming events</li>
              )}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
