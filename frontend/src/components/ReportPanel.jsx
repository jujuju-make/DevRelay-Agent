import { useState, useEffect } from 'react'
import {
  ArrowLeft,
  FileText,
  Calendar,
  Hash,
  ExternalLink,
  Loader2,
  AlertCircle,
  BookOpen,
  Globe,
  Github,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'

function safeFormatDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString('zh-CN')
  } catch {
    return ''
  }
}

function safeFormatDateTime(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleString('zh-CN')
  } catch {
    return ''
  }
}

function parseSources(sourcesStr) {
  if (!sourcesStr) return []
  try {
    return JSON.parse(sourcesStr)
  } catch {
    return sourcesStr.split(',').map((s) => s.trim()).filter(Boolean)
  }
}

export default function ReportPanel({ apiBase, reportId, onBack }) {
  const [view, setView] = useState('list')
  const [detailId, setDetailId] = useState(null)
  const [report, setReport] = useState(null)
  const [allReports, setAllReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (reportId) {
      setView('detail')
      setDetailId(reportId)
    } else {
      setView('list')
      setDetailId(null)
    }
  }, [reportId])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        if (view === 'detail' && detailId) {
          const resp = await fetch(`${apiBase}/reports/${detailId}`)
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
          const data = await resp.json()
          if (!cancelled) setReport(data)
        } else {
          const resp = await fetch(`${apiBase}/reports?limit=20&offset=0`)
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
          const data = await resp.json()
          if (!cancelled) {
            setAllReports(data.items || [])
            setReport(null)
          }
        }
      } catch (err) {
        if (!cancelled) {
          console.error('[ReportPanel]', err.message)
          setError(err.message)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [apiBase, view, detailId])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-neutral-600">
          <Loader2 size={28} className="animate-spin text-emerald-400/60" />
          <span className="text-sm">加载报告...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-neutral-500">
          <AlertCircle size={28} className="text-red-400/60" />
          <span className="text-sm">加载失败：{error}</span>
          <button onClick={() => window.location.reload()} className="text-xs text-emerald-400 hover:text-emerald-300 underline underline-offset-2">刷新页面</button>
        </div>
      </div>
    )
  }

  if (view === 'detail' && report) {
    const sources = parseSources(report.sources)
    const handleBack = () => {
      if (reportId) {
        onBack()
      } else {
        setView('list')
        setDetailId(null)
        setReport(null)
      }
    }
    return (
      <div className="h-full flex flex-col max-w-4xl mx-auto px-4 py-6">
        <div className="shrink-0 mb-4">
          <button onClick={handleBack} className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-300 transition-colors">
            <ArrowLeft size={14} />
            {reportId ? '返回监控流' : '返回报告列表'}
          </button>
        </div>

        <div className="shrink-0 mb-6">
          <h1 className="text-xl font-semibold text-neutral-100 leading-snug">{report.title}</h1>
          <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-neutral-500">
            {report.repo_owner && (
              <span className="flex items-center gap-1"><Github size={12} />{report.repo_owner}/{report.repo_name}</span>
            )}
            <span className="flex items-center gap-1"><Calendar size={12} />{safeFormatDateTime(report.created_at)}</span>
            <span className="flex items-center gap-1"><Hash size={12} />报告 #{report.id}</span>
            {report.query && <span className="flex items-center gap-1 text-neutral-600">问题："{report.query}"</span>}
          </div>
        </div>

        {sources.length > 0 && (
          <div className="shrink-0 mb-4">
            <details className="text-xs text-neutral-500">
              <summary className="cursor-pointer hover:text-neutral-300 select-none inline-flex items-center gap-1">
                <Globe size={12} />
                来源（{sources.length}）
              </summary>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {sources.map((src, idx) => (
                  <span key={idx} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-neutral-900 border border-neutral-800 text-xs text-neutral-400 font-mono">
                    <ExternalLink size={10} />{src}
                  </span>
                ))}
              </div>
            </details>
          </div>
        )}

        <div className="flex-1 overflow-y-auto pr-1">
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
              components={{
                h1: ({ node, ...props }) => <h1 className="text-lg font-semibold text-neutral-100 mt-6 mb-3" {...props} />,
                h2: ({ node, ...props }) => <h2 className="text-base font-semibold text-neutral-100 mt-5 mb-2" {...props} />,
                h3: ({ node, ...props }) => <h3 className="text-sm font-semibold text-neutral-200 mt-4 mb-2" {...props} />,
                p: ({ node, ...props }) => <p className="text-sm leading-relaxed text-neutral-300 my-2" {...props} />,
                a: ({ node, ...props }) => <a {...props} className="text-emerald-400 hover:text-emerald-300 underline underline-offset-2" target="_blank" />,
                code: ({ node, className, children, ...props }) => {
                  if (!className) return <code className="px-1 py-0.5 rounded bg-neutral-800 text-emerald-300 text-[13px] font-mono" {...props}>{children}</code>
                  return <pre className="overflow-x-auto rounded-lg bg-neutral-900 border border-neutral-800 p-3 my-3 text-[13px]"><code className={className} {...props}>{children}</code></pre>
                },
                ul: ({ node, ...props }) => <ul className="text-sm text-neutral-300 space-y-1 my-2 list-disc list-inside" {...props} />,
                ol: ({ node, ...props }) => <ol className="text-sm text-neutral-300 space-y-1 my-2 list-decimal list-inside" {...props} />,
                blockquote: ({ node, ...props }) => <blockquote className="border-l-2 border-emerald-500/30 pl-4 italic text-neutral-400 my-3" {...props} />,
                hr: ({ node, ...props }) => <hr className="border-neutral-800 my-6" {...props} />,
              }}
            >
              {report.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col max-w-4xl mx-auto px-4 py-6">
      <div className="shrink-0 mb-5">
        <h1 className="text-lg font-semibold text-neutral-100 flex items-center gap-2">
          <BookOpen size={20} className="text-emerald-400" />
          归档报告
        </h1>
        <p className="text-xs text-neutral-500 mt-0.5">浏览所有已保存的技术报告</p>
      </div>

      {allReports.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-neutral-500">
            <BookOpen size={28} className="text-neutral-600" />
            <span className="text-sm">暂无报告</span>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {allReports.map((r) => (
            <button
              key={r.id}
              onClick={() => { setView('detail'); setDetailId(r.id) }}
              className="w-full text-left group flex items-start gap-3 p-3 rounded-xl bg-neutral-900/40 border border-neutral-800/40 hover:bg-neutral-900 hover:border-neutral-700/60 transition-all duration-150"
            >
              <div className="shrink-0 w-9 h-9 rounded-lg bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center mt-0.5">
                <FileText size={16} className="text-emerald-400/70" />
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium text-neutral-200 truncate block">{r.title || '(无标题)'}</span>
                <div className="flex items-center gap-3 mt-1 text-xs text-neutral-500">
                  {r.repo_owner ? (
                    <span className="font-mono">{r.repo_owner}/{r.repo_name}</span>
                  ) : (
                    <span>{safeFormatDate(r.created_at)}</span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
