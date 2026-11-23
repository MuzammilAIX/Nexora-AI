import type { Notification } from '../hooks/useNotifications'
import { AlertTriangle, CheckCircle2, X } from 'lucide-react'
import { Link } from 'react-router-dom'

export function NotificationDropdown({ items, open, onClose }: { items: Notification[]; open: boolean; onClose: () => void }) {
  if (!open) return null
  return (
    <>
      <div className="fixed inset-0 z-20" onClick={onClose} />
      <div className="absolute right-0 top-12 w-96 max-h-[500px] overflow-y-auto bg-background border border-border rounded-xl shadow-xl z-30">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Notifications</h3>
          <button onClick={onClose} className="text-muted hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        {items.length === 0 ? (
          <div className="p-8 text-center text-muted text-sm">You are all caught up</div>
        ) : (
          <div className="divide-y divide-border">
            {items.map((n) => (
              <Link key={n.id} to={n.link} onClick={onClose}
                className="flex gap-3 px-4 py-3 hover:bg-backgroundHover transition-colors">
                <div className="mt-0.5">
                  {n.kind === 'approval'
                    ? <AlertTriangle className="w-4 h-4 text-warning" />
                    : <CheckCircle2 className="w-4 h-4 text-danger" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white truncate">{n.title}</p>
                  <p className="text-xs text-muted truncate">{n.subtitle}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  )
}