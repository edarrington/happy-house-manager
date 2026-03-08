'use client'

import { useState } from 'react'
import Header from '@/components/Header'
import { useCalendarEvents, useCreateEvent, useDeleteEvent, type EventCreatePayload } from '@/hooks/useCalendar'
import { Plus, Trash2, X, Calendar } from 'lucide-react'

function formatEventTime(event: { start: { dateTime?: string; date?: string } }): string {
  if (event.start.dateTime) {
    return new Date(event.start.dateTime).toLocaleString()
  }
  return event.start.date ?? ''
}

export default function CalendarPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<Partial<EventCreatePayload>>({})

  const { data, isLoading, refetch } = useCalendarEvents()
  const createEvent = useCreateEvent()
  const deleteEvent = useDeleteEvent()

  const handleCreate = async () => {
    if (!form.summary || !form.start || !form.end) return
    await createEvent.mutateAsync(form as EventCreatePayload)
    setShowCreate(false)
    setForm({})
  }

  return (
    <div className="flex flex-col flex-1">
      <Header title="Calendar" subtitle="Your schedule" />
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-semibold text-gray-700">Upcoming Events</h3>
          <div className="flex gap-2">
            <button onClick={() => refetch()} className="btn-secondary text-sm">Refresh</button>
            <button onClick={() => setShowCreate(true)} className="btn-primary text-sm">
              <Plus size={16} /> New Event
            </button>
          </div>
        </div>

        {isLoading ? (
          <p className="text-gray-400">Loading events...</p>
        ) : (
          <div className="space-y-3">
            {data?.events.map((evt) => (
              <div key={evt.id} className="card p-4 flex items-start justify-between hover:shadow-sm">
                <div className="flex gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg mt-0.5">
                    <Calendar size={16} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{evt.summary}</p>
                    <p className="text-sm text-gray-500">{formatEventTime(evt)}</p>
                    {evt.description && (
                      <p className="text-sm text-gray-400 mt-1">{evt.description}</p>
                    )}
                    {evt.attendees && evt.attendees.length > 0 && (
                      <p className="text-xs text-gray-400 mt-1">
                        {evt.attendees.map((a) => a.email).join(', ')}
                      </p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => deleteEvent.mutate({ eventId: evt.id })}
                  className="text-gray-300 hover:text-red-500 transition-colors ml-4"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            {!data?.events.length && (
              <p className="text-gray-400">No upcoming events.</p>
            )}
          </div>
        )}
      </div>

      {/* Create event modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">New Event</h3>
              <button onClick={() => setShowCreate(false)}><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <input
                className="input"
                placeholder="Event title *"
                value={form.summary ?? ''}
                onChange={(e) => setForm({ ...form, summary: e.target.value })}
              />
              <textarea
                className="input resize-none h-20"
                placeholder="Description"
                value={form.description ?? ''}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Start *</label>
                <input
                  type="datetime-local"
                  className="input"
                  onChange={(e) => setForm({ ...form, start: new Date(e.target.value).toISOString() })}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">End *</label>
                <input
                  type="datetime-local"
                  className="input"
                  onChange={(e) => setForm({ ...form, end: new Date(e.target.value).toISOString() })}
                />
              </div>
              <input
                className="input"
                placeholder="Attendee emails (comma separated)"
                onChange={(e) =>
                  setForm({
                    ...form,
                    attendees: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                  })
                }
              />
              <div className="flex justify-end gap-2">
                <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
                <button onClick={handleCreate} className="btn-primary">
                  <Plus size={14} /> Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
