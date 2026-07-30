import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { Avatar } from '@/components/ui/Avatar'

export function AccountMenu() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (!user) return null

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-md px-1.5 py-1 hover:bg-slate-100 dark:hover:bg-slate-800"
        aria-label="Account menu"
        aria-expanded={open}
      >
        <Avatar username={user.username} avatarUrl={user.avatar_url} size={28} />
        <span className="hidden text-sm text-slate-600 dark:text-slate-300 sm:inline">{user.username}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-30 mt-2 w-56 rounded-md border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-slate-900">
          <div className="border-b border-slate-100 px-3 py-2 dark:border-slate-800">
            <p className="truncate text-sm font-medium">{user.username}</p>
            {user.email && <p className="truncate text-xs text-slate-500 dark:text-slate-400">{user.email}</p>}
          </div>
          <Link
            to="/settings/profile"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Profile
          </Link>
          <Link
            to="/settings/sessions"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Sessions & devices
          </Link>
          <Link
            to="/settings/api-keys"
            onClick={() => setOpen(false)}
            className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            API keys
          </Link>
          <button
            type="button"
            onClick={() => {
              setOpen(false)
              logout()
            }}
            className="block w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-slate-100 dark:text-red-400 dark:hover:bg-slate-800"
          >
            Log out
          </button>
        </div>
      )}
    </div>
  )
}
