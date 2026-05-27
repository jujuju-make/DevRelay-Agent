import { useState, useEffect, useCallback } from 'react'
import {
  FileText,
  ChevronRight,
  Calendar,
  Hash,
  ExternalLink,
  GitCommit,
  BookOpen,
  Search,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'

const PAGE_SIZE = 20

export default function MonitorPanel({ apiBase, onViewReport }) {
  const [reports, setReports] = useState([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchReports = useCallback(async (currentOffset) => {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch(
        `${apiBase}/reports?limit=${PAGE_SIZE}&offset=${currentOffset}`
      )
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setReports(data.items || [])
      setTotal(data.total || 0)
    } catch (err) {
      setError(err.message)
      setReports([])
    } finally {
      setLoading(false)
    }
  }, [apiBase])

  useEffect(() => {
    fetchReports(0)
  }, [fetchReports])

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  const handlePrev = () => {
    const newOffset = Math.max(0, offset - PAGE_SIZE)
    setOffset(newOffset)
    fetchReports(newOffset)
  }

  const handleNext = () => {
    const newOffset = offset + PAGE_SIZE
    if (newOffset < total) {
      setOffset(newOffset)
      fetchReports(newOffset)
    }
  }

  // Filter by search term (client-side)
  const filteredReports = searchTerm.trim()
    ? reports.filter(
        (r) =>
          r.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          r.repo_owner?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          r.repo_name?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : reports

  return (
    <div className="h-full flex flex-col max-w-4xl mx-auto px-4 py-6">
      {/* ── Header ── */}
      <div className="shrink-0 flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-semibold text-neutral-100 flex items-center gap-2">
            <GitCommit size={20} className="text-emerald-400" />
            GitHub 监控流
          </h1>
          <p className="text-xs text-neutral-500 mt-0.5">
            已归档 {total} 份技术报告
          </p>
        </div>

        <button
          onClick={() => fetchReports(offset)}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-neutral-400 bg-neutral-900 border border-neutral-800 hover:border-neutral-700 hover:text-neutral-200 disabled:opacity-40 transition-all"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          刷新
        </button>
      </div>

      {/* ── Search ── */}
      <div className="shrink-0 relative mb-4">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-600"
        />
        <input
          type="text"
          placeholder="搜索报告标题或仓库名…"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full bg-neutral-900 border border-neutral-800 rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-300 placeholder-neutral-600 outline-none focus:border-neutral-700 transition-colors"
        />
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-neutral-600">
            <RefreshCw size={24} className="animate-spin text-emerald-400/60" />
            <span className="text-sm">加载中...</span>
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {!loading && error && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-neutral-500">
            <AlertCircle size={28} className="text-red-400/60" />
            <span className="text-sm">加载失败：{error}</span>
            <button
              onClick={() => fetchReports(offset)}
              className="text-xs text-emerald-400 hover:text-emerald-300 underline underline-offset-2"
            >
              重试
            </button>
          </div>
        </div>
      )}

      {/* ── Empty ── */}
      {!loading && !error && filteredReports.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-neutral-500">
            <BookOpen size={28} className="text-neutral-600" />
            <span className="text-sm">
              {searchTerm.trim() ? '没有匹配的报告' : '暂无归档报告'}
            </span>
            <span className="text-xs text-neutral-600">
              在 AI 对话中让 Agent 生成并保存报告
            </span>
          </div>
        </div>
      )}

      {/* ── Report List ── */}
      {!loading && !error && filteredReports.length > 0 && (
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {filteredReports.map((report) => (
            <button
              key={report.id}
              onClick={() => onViewReport(report.id)}
              className="w-full text-left group flex items-start gap-3 p-3 rounded-xl bg-neutral-900/40 border border-neutral-800/40 hover:bg-neutral-900 hover:border-neutral-700/60 transition-all duration-150 animate-fade-in"
            >
              {/* Icon */}
              <div className="shrink-0 w-9 h-9 rounded-lg bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center mt-0.5">
                <FileText size={16} className="text-emerald-400/70" />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-neutral-200 truncate">
                    {report.title}
                  </span>
                  {report.repo_owner && (
                    <span className="shrink-0 text-[11px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-500 font-mono">
                      {report.repo_owner}/{report.repo_name}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs text-neutral-500">
                  {report.query && (
                    <span className="truncate max-w-[200px]">
                      "{report.query}"
                    </span>
                  )}
                  <span className="flex items-center gap-1 shrink-0">
                    <Calendar size={11} />
                    {formatDate(report.created_at)}
                  </span>
                  <span className="flex items-center gap-1 shrink-0">
                    <Hash size={11} />
                    {report.id}
                  </span>
                </div>
              </div>

              {/* Arrow */}
              <ChevronRight
                size={16}
                className="shrink-0 text-neutral-600 group-hover:text-neutral-400 transition-colors mt-1.5"
              />
            </button>
          ))}
        </div>
      )}

      {/* ── Pagination ── */}
      {!loading && !error && total > PAGE_SIZE && (
        <div className="shrink-0 flex items-center justify-between pt-4 border-t border-neutral-800/50 mt-4">
          <span className="text-xs text-neutral-600">
            第 {currentPage} / {totalPages} 页 · 共 {total} 条
          </span>
          <div className="flex gap-2">
            <button
              onClick={handlePrev}
              disabled={offset === 0}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-neutral-400 bg-neutral-900 border border-neutral-800 hover:border-neutral-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              上一页
            </button>
            <button
              onClick={handleNext}
              disabled={offset + PAGE_SIZE >= total}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-neutral-400 bg-neutral-900 border border-neutral-800 hover:border-neutral-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
