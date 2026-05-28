import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, User, Square, Check, X, Database } from 'lucide-react'
import ReactMarkdown from 'react-markdown'


export default function ChatPanel({ apiBase, sessionId, messages, setMessages }) {
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [pendingArchive, setPendingArchive] = useState(false)
  const [archiving, setArchiving] = useState(false)
  const [repoInput, setRepoInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = useCallback(async (queryOverride) => {
    const query = queryOverride ?? input.trim()
    if (!query || streaming) return

    setInput('')
    setPendingArchive(false)

    const userMsg = { role: 'user', content: query }
    setMessages((prev) => [...prev, userMsg])

    const assistantMsg = { role: 'assistant', content: '' }
    setMessages((prev) => [...prev, assistantMsg])
    setStreaming(true)

    let fullAnswer = ''
    let shouldOfferArchive = false

    try {
      const resp = await fetch(`${apiBase}/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: sessionId }),
      })

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}))
        throw new Error(errData.detail || `HTTP ${resp.status}`)
      }
      const data = await resp.json()
      fullAnswer = data.answer || '（Agent 未返回内容）'
      shouldOfferArchive = data.pending_archive || false

      // Typewriter streaming effect
      let currentContent = ''
      let idx = 0
      const chunkSize = 2
      const interval = setInterval(() => {
        if (idx >= fullAnswer.length) {
          clearInterval(interval)
          setStreaming(false)
          // 打字完成后才设置归档按钮状态
          if (shouldOfferArchive) {
            setPendingArchive(true)
          }
          return
        }
        const end = Math.min(idx + chunkSize, fullAnswer.length)
        currentContent += fullAnswer.slice(idx, end)
        idx = end
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: currentContent,
          }
          return updated
        })
      }, 20)
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `⚠️ 请求失败：${err.message}`,
        }
        return updated
      })
      setStreaming(false)
    }
  }, [input, streaming, apiBase, sessionId, setMessages])

  const handleArchiveDecision = useCallback(async (decision) => {
    if (archiving) return
    setArchiving(true)
    setPendingArchive(false)

    const decisionText = decision === 'accept' ? '归档' : '跳过'
    setMessages((prev) => [...prev, { role: 'user', content: decisionText }])

    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    try {
      const resp = await fetch(`${apiBase}/agent/archive-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, decision }),
      })

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}))
        throw new Error(errData.detail || `HTTP ${resp.status}: ${resp.statusText}`)
      }
      const data = await resp.json()

      const fullAnswer = data.answer
      let currentContent = ''
      let idx = 0
      const chunkSize = 2
      const interval = setInterval(() => {
        if (idx >= fullAnswer.length) {
          clearInterval(interval)
          setArchiving(false)
          return
        }
        const end = Math.min(idx + chunkSize, fullAnswer.length)
        currentContent += fullAnswer.slice(idx, end)
        idx = end
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = { ...updated[updated.length - 1], content: currentContent }
          return updated
        })
      }, 20)
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: `⚠️ 归档请求失败：${err.message}` }
        return updated
      })
      setArchiving(false)
    }
  }, [archiving, apiBase, sessionId, setMessages])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleQuickRepo = useCallback(() => {
    const trimmed = repoInput.trim()
    if (!trimmed || streaming) return
    const parts = trimmed.split('/')
    if (parts.length < 2) return
    const query = `查看 ${parts[0]}/${parts[1]} 的最新提交`
    setRepoInput('')
    handleSend(query)
  }, [repoInput, streaming, handleSend])

  const isBusy = streaming || archiving

  return (
    <div className="h-full flex flex-col max-w-4xl mx-auto">
      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 animate-slide-up ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="shrink-0 w-8 h-8 mt-0.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <Bot size={16} className="text-emerald-400" />
              </div>
            )}

            <div
              className={`max-w-[80%] lg:max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-neutral-800 text-neutral-100 rounded-br-md'
                  : 'bg-neutral-900/50 text-neutral-300 rounded-bl-md border border-neutral-800/50'
              }`}
            >
              {msg.role === 'assistant' ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown
                    components={{
                      a: ({ node, ...props }) => (
                        <a {...props} className="text-emerald-400 hover:text-emerald-300 underline underline-offset-2" target="_blank" />
                      ),
                      code: ({ node, className, children, ...props }) => {
                        const isInline = !className
                        if (isInline) {
                          return <code className="px-1 py-0.5 rounded bg-neutral-800 text-emerald-300 text-[13px] font-mono" {...props}>{children}</code>
                        }
                        return (
                          <pre className="overflow-x-auto rounded-lg bg-neutral-900 border border-neutral-800 p-3 text-[13px]">
                            <code className={className} {...props}>{children}</code>
                          </pre>
                        )
                      },
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>

                  {/* ⭐ 归档确认按钮：仅在打字完成后显示 */}
                  {pendingArchive && idx === messages.length - 1 && !streaming && (
                    <div className="flex items-center gap-2 mt-3 pt-3 border-t border-neutral-800 animate-fade-in">
                      <span className="text-xs text-neutral-500 flex items-center gap-1">
                        <Database size={12} />
                        保存到数据库？
                      </span>
                      <button
                        onClick={() => handleArchiveDecision('accept')}
                        disabled={archiving}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-40 transition-all"
                      >
                        <Check size={12} />
                        确认归档
                      </button>
                      <button
                        onClick={() => handleArchiveDecision('reject')}
                        disabled={archiving}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-neutral-800 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-700 disabled:opacity-40 transition-all"
                      >
                        <X size={12} />
                        跳过
                      </button>
                    </div>
                  )}

                  {(streaming && idx === messages.length - 1) && (
                    <span className="typing-cursor" />
                  )}
                </div>
              ) : (
                <span className="whitespace-pre-wrap">{msg.content}</span>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="shrink-0 w-8 h-8 mt-0.5 rounded-lg bg-neutral-700 border border-neutral-600/50 flex items-center justify-center">
                <User size={16} className="text-neutral-300" />
              </div>
            )}
          </div>
        ))}

        {/* Streaming loading indicator */}
        {isBusy && messages[messages.length - 1]?.content === '' && (
          <div className="flex gap-3 animate-fade-in">
            <div className="shrink-0 w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Bot size={16} className="text-emerald-400" />
            </div>
            <div className="max-w-[80%] rounded-2xl rounded-bl-md px-4 py-3 bg-neutral-900/50 border border-neutral-800/50">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" />
                <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" style={{ animationDelay: '0.2s' }} />
                <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Quick Repo Input (above chat bar) ── */}
      <div className="shrink-0 px-4 pb-2">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-neutral-900/50 border border-neutral-800/50">
            <GithubIcon className="shrink-0 text-neutral-500 ml-1" size={14} />
            <input
              type="text"
              placeholder="快速追踪：输入 owner/repo（如 fastapi/fastapi）"
              value={repoInput}
              onChange={(e) => setRepoInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleQuickRepo()}
              className="flex-1 bg-transparent text-sm text-neutral-300 placeholder-neutral-600 outline-none"
            />
            <button
              onClick={handleQuickRepo}
              disabled={!repoInput.trim() || isBusy}
              className="px-2.5 py-1 rounded-md text-xs font-medium bg-neutral-800 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              追踪
            </button>
          </div>
        </div>
      </div>

      {/* ── Input Bar ── */}
      <div className="shrink-0 px-4 pb-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-2 p-2 rounded-xl bg-neutral-900 border border-neutral-800 focus-within:border-neutral-700 transition-colors">
            <textarea
              ref={inputRef}
              placeholder={pendingArchive ? '请先确认是否归档...' : '输入你的技术问题…'}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isBusy}
              className="flex-1 bg-transparent text-sm text-neutral-100 placeholder-neutral-600 outline-none resize-none max-h-32 py-1.5 px-2 disabled:opacity-40"
              style={{ minHeight: '2rem' }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px'
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isBusy}
              className="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              {isBusy ? <Square size={15} fill="currentColor" /> : <Send size={15} />}
            </button>
          </div>
          <p className="mt-1.5 text-[11px] text-neutral-600 text-center">
            DevRelay AI Agent · 回答完成后可按「确认归档」保存到数据库
          </p>
        </div>
      </div>
    </div>
  )
}

function GithubIcon({ className, size }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 3 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  )
}
