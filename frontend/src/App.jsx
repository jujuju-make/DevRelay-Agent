import { useState, useRef, useCallback, useEffect } from 'react'
import { Menu, X, Terminal, Github } from 'lucide-react'
import ChatPanel from './components/ChatPanel'
import MonitorPanel from './components/MonitorPanel'
import ReportPanel from './components/ReportPanel'

const API_BASE = '/api/v1'

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: [
    '# 👋 欢迎使用 DevRelay',
    '',
    '我是你的 **AI 技术监控助手**，可以帮你：',
    '',
    '- 🔍 **追踪 GitHub 仓库** — 输入 owner/repo 查看最新 commit',
    '- 🌐 **全网搜索** — 查找技术文档、教程、评测',
    '- 📝 **生成技术报告** — 自动整理成结构化报告并归档',
    '',
    '**试试输入：** "查看 fastapi/fastapi 的最新提交"',
  ].join('\n'),
}

export default function App() {
  const [activeView, setActiveView] = useState('chat')       // chat | monitor | report
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [selectedReportId, setSelectedReportId] = useState(null)

  // ── Chat state lifted up so it persists across tab switches ──
  const [messages, setMessages] = useState([WELCOME_MESSAGE])

  // Generate a stable session_id per browser tab
  const sessionIdRef = useRef(
    'web-' + Math.random().toString(36).slice(2, 10)
  )

  const handleViewReport = useCallback((reportId) => {
    setSelectedReportId(reportId)
    setActiveView('report')
    setMobileMenuOpen(false)
  }, [])

  const handleBackToMonitor = useCallback(() => {
    setSelectedReportId(null)
    setActiveView('monitor')
  }, [])

  return (
    <div className="h-screen flex flex-col bg-neutral-950">
      {/* ── Top Bar ── */}
      <header className="shrink-0 h-12 border-b border-neutral-800 flex items-center justify-between px-4 lg:px-6">
        <div className="flex items-center gap-3">
          <button
            className="lg:hidden p-1.5 rounded-md hover:bg-neutral-800 text-neutral-400 hover:text-neutral-200 transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <div className="flex items-center gap-2">
            <Terminal size={18} className="text-emerald-400" />
            <span className="text-sm font-semibold text-neutral-100 tracking-tight">DevRelay</span>
          </div>
          <span className="hidden sm:inline text-[11px] text-neutral-600 font-mono">v0.1.0</span>
        </div>

        {/* Desktop Nav */}
        <nav className="hidden lg:flex items-center gap-1">
          <NavBtn active={activeView === 'chat'} onClick={() => setActiveView('chat')}>
            AI 对话
          </NavBtn>
          <NavBtn active={activeView === 'monitor'} onClick={() => setActiveView('monitor')}>
            GitHub 监控
          </NavBtn>
          <NavBtn active={activeView === 'report'} onClick={() => setActiveView('report')}>
            归档报告
          </NavBtn>
        </nav>

        <div className="flex items-center gap-2">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-md hover:bg-neutral-800 text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            <Github size={16} />
          </a>
          <div className="w-6 h-6 rounded-full bg-neutral-700 flex items-center justify-center text-[11px] font-medium text-neutral-300">
            D
          </div>
        </div>
      </header>

      {/* ── Mobile Nav Dropdown ── */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-neutral-800 bg-neutral-900/80 backdrop-blur-sm animate-fade-in">
          <div className="flex flex-col p-2 gap-0.5">
            <MobileNavBtn active={activeView === 'chat'} onClick={() => { setActiveView('chat'); setMobileMenuOpen(false) }}>
              💬 AI 对话
            </MobileNavBtn>
            <MobileNavBtn active={activeView === 'monitor'} onClick={() => { setActiveView('monitor'); setMobileMenuOpen(false) }}>
              📡 GitHub 监控
            </MobileNavBtn>
            <MobileNavBtn active={activeView === 'report'} onClick={() => { setActiveView('report'); setMobileMenuOpen(false) }}>
              📄 归档报告
            </MobileNavBtn>
          </div>
        </div>
      )}

      {/* ── Main Content ── */}
      <main className="flex-1 overflow-hidden">
        {activeView === 'chat' && (
          <ChatPanel
            apiBase={API_BASE}
            sessionId={sessionIdRef.current}
            messages={messages}
            setMessages={setMessages}
          />
        )}
        {activeView === 'monitor' && (
          <MonitorPanel apiBase={API_BASE} onViewReport={handleViewReport} />
        )}
        {activeView === 'report' && (
          <ReportPanel
            apiBase={API_BASE}
            reportId={selectedReportId}
            onBack={handleBackToMonitor}
          />
        )}
      </main>
    </div>
  )
}

/* ── Inline Sub-components ── */

function NavBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-150 ${
        active
          ? 'bg-neutral-800 text-neutral-100'
          : 'text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50'
      }`}
    >
      {children}
    </button>
  )
}

function MobileNavBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
        active ? 'bg-neutral-800 text-neutral-100' : 'text-neutral-400 hover:text-neutral-200'
      }`}
    >
      {children}
    </button>
  )
}
