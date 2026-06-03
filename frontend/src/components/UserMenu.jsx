import { useState, useRef, useEffect } from 'react'
import { LogOut, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function UserMenu() {
  const { username, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)

  // Click outside to close
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const initial = username ? username.charAt(0).toUpperCase() : '?'

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="w-7 h-7 rounded-full bg-neutral-700 hover:bg-neutral-600 flex items-center justify-center text-xs font-medium text-neutral-200 transition-colors"
        title={username}
      >
        {initial}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-44 rounded-lg bg-neutral-900 border border-neutral-800 shadow-xl shadow-black/30 animate-fade-in z-50">
          <div className="px-3 py-2 border-b border-neutral-800">
            <p className="text-xs text-neutral-400 truncate">{username}</p>
          </div>
          <button
            onClick={() => {
              setOpen(false)
              logout()
            }}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800 rounded-b-lg transition-colors"
          >
            <LogOut size={13} />
            退出登录
          </button>
        </div>
      )}
    </div>
  )
}
