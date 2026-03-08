'use client'

import { useState } from 'react'
import Header from '@/components/Header'
import { useGmailMessages, useGmailMessage, useSendEmail, useReplyEmail } from '@/hooks/useGmail'
import { Mail, Send, RefreshCw, X, Reply } from 'lucide-react'
import clsx from 'clsx'

export default function GmailPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [composing, setComposing] = useState(false)
  const [replying, setReplying] = useState(false)
  const [composeTo, setComposeTo] = useState('')
  const [composeSubject, setComposeSubject] = useState('')
  const [composeBody, setComposeBody] = useState('')

  const { data, isLoading, refetch } = useGmailMessages(20)
  const { data: detail, isLoading: detailLoading } = useGmailMessage(selectedId)
  const sendEmail = useSendEmail()
  const replyEmail = useReplyEmail()

  const handleSend = async () => {
    await sendEmail.mutateAsync({ to: composeTo, subject: composeSubject, body: composeBody })
    setComposing(false)
    setComposeTo('')
    setComposeSubject('')
    setComposeBody('')
  }

  const handleReply = async () => {
    if (!detail) return
    await replyEmail.mutateAsync({
      thread_id: detail.threadId,
      message_id: detail.id,
      body: composeBody,
      to: detail.from,
    })
    setReplying(false)
    setComposeBody('')
  }

  return (
    <div className="flex flex-col flex-1">
      <Header title="Gmail" subtitle="Your inbox" />
      <div className="flex flex-1 overflow-hidden">
        {/* Message list */}
        <div className="w-96 border-r border-gray-200 flex flex-col bg-white">
          <div className="p-4 border-b flex items-center justify-between">
            <button onClick={() => setComposing(true)} className="btn-primary text-xs">
              <Mail size={14} /> Compose
            </button>
            <button onClick={() => refetch()} className="btn-secondary text-xs">
              <RefreshCw size={14} />
            </button>
          </div>
          <ul className="flex-1 overflow-y-auto divide-y divide-gray-100">
            {isLoading && <li className="p-4 text-sm text-gray-400">Loading...</li>}
            {data?.messages.map((msg) => (
              <li
                key={msg.id}
                onClick={() => setSelectedId(msg.id)}
                className={clsx(
                  'px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors',
                  selectedId === msg.id && 'bg-blue-50 border-l-2 border-l-blue-500'
                )}
              >
                <p className="text-sm font-medium text-gray-900 truncate">{msg.subject}</p>
                <p className="text-xs text-gray-500 truncate">{msg.from}</p>
                <p className="text-xs text-gray-400 truncate mt-1">{msg.snippet}</p>
              </li>
            ))}
          </ul>
        </div>

        {/* Message detail */}
        <div className="flex-1 flex flex-col bg-white overflow-y-auto">
          {selectedId && detail ? (
            <div className="p-6">
              <h2 className="text-xl font-semibold mb-2">{detail.subject}</h2>
              <div className="text-sm text-gray-500 mb-4">
                <p>From: {detail.from}</p>
                <p>To: {detail.to}</p>
                <p>Date: {detail.date}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-sm whitespace-pre-wrap font-mono">
                {detail.body}
              </div>
              <button
                onClick={() => { setReplying(true); setComposeBody('') }}
                className="btn-secondary mt-4 text-sm"
              >
                <Reply size={14} /> Reply
              </button>

              {replying && (
                <div className="mt-4 border rounded-lg p-4">
                  <textarea
                    className="input resize-none h-32"
                    placeholder="Write your reply..."
                    value={composeBody}
                    onChange={(e) => setComposeBody(e.target.value)}
                  />
                  <div className="flex gap-2 mt-2">
                    <button onClick={handleReply} className="btn-primary text-sm">
                      <Send size={14} /> Send Reply
                    </button>
                    <button onClick={() => setReplying(false)} className="btn-secondary text-sm">
                      <X size={14} /> Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center flex-1 text-gray-400">
              Select a message to read
            </div>
          )}
        </div>
      </div>

      {/* Compose modal */}
      {composing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">New Message</h3>
              <button onClick={() => setComposing(false)}><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <input className="input" placeholder="To" value={composeTo} onChange={(e) => setComposeTo(e.target.value)} />
              <input className="input" placeholder="Subject" value={composeSubject} onChange={(e) => setComposeSubject(e.target.value)} />
              <textarea
                className="input resize-none h-40"
                placeholder="Message body"
                value={composeBody}
                onChange={(e) => setComposeBody(e.target.value)}
              />
              <div className="flex justify-end gap-2">
                <button onClick={() => setComposing(false)} className="btn-secondary">Cancel</button>
                <button onClick={handleSend} className="btn-primary">
                  <Send size={14} /> Send
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
