import { useState } from 'react'
import { Terminal, LogIn, User, Lock, Mail, AlertCircle, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const API_BASE = '/api/v1'

export default function LoginPage() {
  const { login } = useAuth()
  const [mode, setMode] = useState('login') // login | register
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const switchMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!username.trim() || !password.trim()) {
      setError('请填写用户名和密码')
      return
    }


    if (mode === 'register') {
      if (!email.trim()) {
        setError('请填写邮箱')
        return
      }
      if (password !== confirmPassword) {
        setError('两次密码输入不一致')
        return
      }
      if (password.length < 6) {
        setError('密码长度至少 6 位')
        return
      }
    }

    setSubmitting(true)

    try {
      const endpoint = mode === 'login' ? 'login' : 'register'
      const body =
        mode === 'login'
          ? { username: username.trim(), password }
          : { username: username.trim(), email: email.trim().toLowerCase(), password }

      const resp = await fetch(`${API_BASE}/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const data = await resp.json()

      if (!resp.ok) {
        throw new Error(data.detail || '请求失败')
      }

      login(data.access_token, data.username)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-950 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <Terminal size={20} className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-neutral-100">DevRelay</h1>
            <p className="text-[11px] text-neutral-500">AI 技术监控助手</p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-6">
          <h2 className="text-base font-semibold text-neutral-100 mb-1">
            {mode === 'login' ? '登录' : '注册'}
          </h2>
          <p className="text-xs text-neutral-500 mb-5">
            {mode === 'login' ? '欢迎回来，请登录你的账号' : '创建新账号开始使用'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label className="block text-xs text-neutral-400 mb-1">用户名</label>
              <div className="relative">
                <User
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500"
                />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="输入用户名"
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-200 placeholder-neutral-600 outline-none focus:border-emerald-500/50 transition-colors"
                />
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-xs text-neutral-400 mb-1">邮箱</label>
                <div className="relative">
                  <Mail
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500"
                  />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-200 placeholder-neutral-600 outline-none focus:border-emerald-500/50 transition-colors"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs text-neutral-400 mb-1">密码</label>
              <div className="relative">
                <Lock
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500"
                />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="输入密码"
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-200 placeholder-neutral-600 outline-none focus:border-emerald-500/50 transition-colors"
                />
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-xs text-neutral-400 mb-1">确认密码</label>
                <div className="relative">
                  <Lock
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500"
                  />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="再次输入密码"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-200 placeholder-neutral-600 outline-none focus:border-emerald-500/50 transition-colors"
                  />
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-1.5 text-red-400 text-xs bg-red-500/5 border border-red-500/20 rounded-lg px-3 py-2">
                <AlertCircle size={12} className="shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium transition-colors"
            >
              {submitting ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <LogIn size={15} />
              )}
              {mode === 'login' ? '登录' : '注册'}
            </button>
          </form>

          <div className="mt-4 text-center">
            <button
              onClick={switchMode}
              className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors"
            >
              {mode === 'login' ? '没有账号？点击注册' : '已有账号？点击登录'}
            </button>
          </div>
        </div>

        <p className="mt-6 text-[11px] text-neutral-700 text-center">
          DevRelay v0.1.0
        </p>
      </div>
    </div>
  )
}
