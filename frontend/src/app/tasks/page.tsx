'use client'

import { useState } from 'react'
import Header from '@/components/Header'
import {
  useTodoistProjects,
  useTodoistTasks,
  useCreateTask,
  useDeleteTask,
  type TaskCreatePayload,
} from '@/hooks/useTodoist'
import { Plus, Trash2, CheckCircle, Circle, X } from 'lucide-react'

export default function TasksPage() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>(undefined)
  const [showCreate, setShowCreate] = useState(false)
  const [newContent, setNewContent] = useState('')
  const [newDue, setNewDue] = useState('')
  const [newPriority, setNewPriority] = useState<number>(1)

  const { data: projectsData, isLoading: projectsLoading } = useTodoistProjects()
  const { data: tasksData, isLoading: tasksLoading } = useTodoistTasks(selectedProjectId)
  const createTask = useCreateTask()
  const deleteTask = useDeleteTask()

  const handleCreate = async () => {
    if (!newContent.trim()) return
    const payload: TaskCreatePayload = {
      content: newContent,
      priority: newPriority,
    }
    if (selectedProjectId) payload.project_id = selectedProjectId
    if (newDue) payload.due_string = newDue
    await createTask.mutateAsync(payload)
    setNewContent('')
    setNewDue('')
    setNewPriority(1)
    setShowCreate(false)
  }

  const priorityColor = (p: number) => {
    if (p === 4) return 'text-red-500'
    if (p === 3) return 'text-orange-500'
    if (p === 2) return 'text-blue-500'
    return 'text-gray-400'
  }

  return (
    <div className="flex flex-col flex-1">
      <Header title="Tasks" subtitle="Powered by Todoist" />
      <div className="flex flex-1 overflow-hidden">
        {/* Project sidebar */}
        <div className="w-56 border-r border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Projects</p>
          {projectsLoading && <p className="text-sm text-gray-400">Loading...</p>}
          <ul className="space-y-1">
            <li>
              <button
                onClick={() => setSelectedProjectId(undefined)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm ${
                  !selectedProjectId ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                All Tasks
              </button>
            </li>
            {projectsData?.projects.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => setSelectedProjectId(p.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate ${
                    selectedProjectId === p.id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {p.name}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Task list */}
        <div className="flex-1 flex flex-col bg-white overflow-y-auto">
          <div className="p-4 border-b flex justify-end">
            <button onClick={() => setShowCreate(true)} className="btn-primary text-sm">
              <Plus size={16} /> Add Task
            </button>
          </div>

          {tasksLoading ? (
            <p className="p-4 text-gray-400">Loading tasks...</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {tasksData?.tasks.map((task) => (
                <li key={task.id} className="flex items-start gap-3 px-6 py-3 hover:bg-gray-50">
                  <Circle size={18} className={`mt-0.5 flex-shrink-0 ${priorityColor(task.priority)}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900">{task.content}</p>
                    {task.due && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        Due: {task.due.string ?? task.due.date}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => deleteTask.mutate(task.id)}
                    className="text-gray-300 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </li>
              ))}
              {!tasksData?.tasks.length && (
                <li className="px-6 py-4 text-sm text-gray-400">No tasks found.</li>
              )}
            </ul>
          )}
        </div>
      </div>

      {/* Create task modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">New Task</h3>
              <button onClick={() => setShowCreate(false)}><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <input
                className="input"
                placeholder="Task name *"
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
              />
              <input
                className="input"
                placeholder="Due date (e.g. tomorrow, next Monday)"
                value={newDue}
                onChange={(e) => setNewDue(e.target.value)}
              />
              <select
                className="input"
                value={newPriority}
                onChange={(e) => setNewPriority(Number(e.target.value))}
              >
                <option value={1}>Priority: Normal</option>
                <option value={2}>Priority: Medium</option>
                <option value={3}>Priority: High</option>
                <option value={4}>Priority: Urgent</option>
              </select>
              <div className="flex justify-end gap-2">
                <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
                <button onClick={handleCreate} className="btn-primary">
                  <Plus size={14} /> Add
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
