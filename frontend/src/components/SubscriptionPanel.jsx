import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, RefreshCw, Bookmark, BookmarkCheck, Github, FileText } from 'lucide-react'

export default function SubscriptionPanel({ apiBase }) {
  const [subs, setSubs] = useState([])
  const [loading, setLoading] = useState(true)
  const [newOwner, setNewOwner] = useState('')
  const [newRepo, setNewRepo] = useState('')
  const [digestRunning, setDigestRunning] = useState(false)
  const [singleRunning, setSingleRunning] = useState({}) // { [subId]: true/false }
  const [digestResult, setDigestResult] = useState(null)
  const [singleResults, setSingleResults] = useState({}) // { [subId]: {...} }

  const loadSubs = useCallback(async () => {
    try {
      setLoading(true)
      const resp = await fetch(`${apiBase}/subscriptions`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setSubs(data.items || [])
    } catch (err) {
      console.error('加载订阅失败:', err)
    } finally {
      setLoading(false)
    }
  }, [apiBase])

  useEffect(() => { loadSubs() }, [loadSubs])

  const handleAdd = useCallback(async () => {
    const owner = newOwner.trim()
    const repo = newRepo.trim()
    if (!owner || !repo) return
    try {
      const resp = await fetch(`${apiBase}/subscriptions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_owner: owner, repo_name: repo, extra_sources: [] }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${resp.status}`)
      }
      setNewOwner('')
      setNewRepo('')
      await loadSubs()
    } catch (err) {
      alert(`添加失败: ${err.message}`)
    }
  }, [newOwner, newRepo, apiBase, loadSubs])

  const handleDelete = useCallback(async (id) => {
    try {
      const resp = await fetch(`${apiBase}/subscriptions/${id}`, { method: 'DELETE' })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      await loadSubs()
    } catch (err) {
      alert(`删除失败: ${err.message}`)
    }
  }, [apiBase, loadSubs])

  const handleToggle = useCallback(async (sub) => {
    try {
      const resp = await fetch(`${apiBase}/subscriptions/${sub.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !sub.active }),
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      await loadSubs()
    } catch (err) {
      alert(`更新失败: ${err.message}`)
    }
  }, [apiBase, loadSubs])

  // ── 为单个订阅生成日报 ──
  const handleSingleDigest = useCallback(async (subId, owner, repo) => {
    setSingleRunning((prev) => ({ ...prev, [subId]: true }))
    setSingleResults((prev) => ({ ...prev, [subId]: null }))
    try {
      const resp = await fetch(`${apiBase}/digest/run/${subId}`, { method: 'POST' })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setSingleResults((prev) => ({ ...prev, [subId]: data }))
    } catch (err) {
      setSingleResults((prev) => ({ ...prev, [subId]: { error: err.message } }))
    } finally {
      setSingleRunning((prev) => ({ ...prev, [subId]: false }))
    }
  }, [apiBase])

  // ── 为所有订阅生成日报 ──
  const handleRunDigest = useCallback(async () => {
    setDigestRunning(true)
    setDigestResult(null)
    try {
      const resp = await fetch(`${apiBase}/digest/run`, { method: 'POST' })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setDigestResult(data)
    } catch (err) {
      setDigestResult({ error: err.message })
    } finally {
      setDigestRunning(false)
    }
  }, [apiBase])

  return (
    <div className="h-full flex flex-col max-w-4xl mx-auto p-4 lg:p-6 overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-neutral-100 flex items-center gap-2">
          <BookmarkCheck size={18} className="text-emerald-400" />
          仓库订阅管理
        </h2>
        <p className="text-sm text-neutral-500 mt-1">
          添加你关注的仓库后，DevRelay 会每天自动生成日报并归档
        </p>
      </div>

      {/* 添加表单 */}
      <div className="flex items-center gap-2 mb-6 p-3 rounded-lg bg-neutral-900/50 border border-neutral-800/50">
        <Github size={16} className="shrink-0 text-neutral-500" />
        <input
          type="text"
          placeholder="owner（如 fastapi）"
          value={newOwner}
          onChange={(e) => setNewOwner(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && document.getElementById('repo-input')?.focus()}
          className="flex-1 bg-transparent text-sm text-neutral-300 placeholder-neutral-600 outline-none min-w-0"
        />
        <span className="text-neutral-600">/</span>
        <input
          id="repo-input"
          type="text"
          placeholder="repo（如 fastapi）"
          value={newRepo}
          onChange={(e) => setNewRepo(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          className="flex-1 bg-transparent text-sm text-neutral-300 placeholder-neutral-600 outline-none min-w-0"
        />
        <button
          onClick={handleAdd}
          disabled={!newOwner.trim() || !newRepo.trim()}
          className="shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          <Plus size={14} />
          添加
        </button>
      </div>

      {/* 订阅列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="flex gap-1.5">
            <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" />
            <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" style={{ animationDelay: '0.2s' }} />
            <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" style={{ animationDelay: '0.4s' }} />
          </div>
        </div>
      ) : subs.length === 0 ? (
        <div className="text-center py-12 text-neutral-500">
          <Bookmark size={32} className="mx-auto mb-3 opacity-50" />
          <p className="text-sm">还没有订阅任何仓库</p>
          <p className="text-xs mt-1">在上面输入 owner/repo 开始添加</p>
        </div>
      ) : (
        <div className="space-y-2">
          {subs.map((sub) => {
            const sr = singleResults[sub.id]
            const isRunning = singleRunning[sub.id]
            return (
              <div
                key={sub.id}
                className={`flex flex-col gap-2 p-3 rounded-lg border transition-all ${
                  sub.active
                    ? 'bg-neutral-900/50 border-neutral-800/50'
                    : 'bg-neutral-900/20 border-neutral-800/20 opacity-50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleToggle(sub)}
                    className="shrink-0 p-1 rounded hover:bg-neutral-800 text-neutral-500 hover:text-neutral-300 transition-colors"
                    title={sub.active ? '暂停订阅' : '启用订阅'}
                  >
                    {sub.active ? <BookmarkCheck size={16} className="text-emerald-400" /> : <Bookmark size={16} />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-neutral-200">
                        {sub.repo_owner}/{sub.repo_name}
                      </span>
                      {sub.active && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
                          活跃
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-neutral-500 mt-0.5">
                      创建于 {new Date(sub.created_at).toLocaleDateString('zh-CN')}
                    </p>
                  </div>

                  {/* ── 单个生成日报按钮 ── */}
                  <button
                    onClick={() => handleSingleDigest(sub.id, sub.repo_owner, sub.repo_name)}
                    disabled={isRunning || !sub.active}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0"
                    title={`为 ${sub.repo_owner}/${sub.repo_name} 生成日报`}
                  >
                    <FileText size={12} className={isRunning ? 'animate-pulse' : ''} />
                    {isRunning ? '生成中...' : '生成日报'}
                  </button>

                  <button
                    onClick={() => handleDelete(sub.id)}
                    className="shrink-0 p-1.5 rounded hover:bg-red-500/10 text-neutral-500 hover:text-red-400 transition-colors"
                    title="删除订阅"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                {/* ── 单条生成结果 ── */}
                {sr && (
                  <div className="ml-10 p-2 rounded bg-neutral-800/50 border border-neutral-700/50">
                    {sr.error ? (
                      <p className="text-xs text-red-400">生成失败: {sr.error}</p>
                    ) : (
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-emerald-400">✓</span>
                        <span className="text-neutral-300">
                          已生成报告 #{sr.results?.[0]?.report_id || '?'}
                        </span>
                        <span className="text-neutral-500">（{new Date().toLocaleTimeString('zh-CN')}）</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── 全部生成日报 ── */}
      <div className="mt-8 pt-6 border-t border-neutral-800">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-neutral-200">为所有活跃仓库生成日报</h3>
            <p className="text-xs text-neutral-500 mt-0.5">
              一键为所有已启用的订阅仓库生成当日日报
            </p>
          </div>
          <button
            onClick={handleRunDigest}
            disabled={digestRunning}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            <RefreshCw size={14} className={digestRunning ? 'animate-spin' : ''} />
            全部生成
          </button>
        </div>

        {digestResult && (
          <div className="mt-3 p-3 rounded-lg bg-neutral-900/50 border border-neutral-800/50">
            {digestResult.error ? (
              <p className="text-sm text-red-400">生成失败: {digestResult.error}</p>
            ) : (
              <div>
                <p className="text-sm text-emerald-400 mb-2">
                  生成了 {digestResult.count} 份日报
                </p>
                <div className="space-y-1">
                  {digestResult.results?.map((r, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      {r.report_id ? (
                        <>
                          <span className="text-emerald-400">✓</span>
                          <span className="text-neutral-300">{r.repo}</span>
                          <span className="text-neutral-500">→ 报告 #{r.report_id}</span>
                        </>
                      ) : (
                        <>
                          <span className="text-red-400">✗</span>
                          <span className="text-neutral-300">{r.repo}</span>
                          <span className="text-red-400">{r.error}</span>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
