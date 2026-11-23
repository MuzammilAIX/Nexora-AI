import { useState, useEffect } from 'react'
import { User, Mail, Shield, LogOut, Building, Key } from 'lucide-react'

export function Settings() {
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    const stored = localStorage.getItem('nexora_user')
    if (stored) {
      try { setUser(JSON.parse(stored)) } catch (e) {}
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('nexora_token')
    localStorage.removeItem('nexora_user')
    window.location.href = '/'
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-white mb-1">Settings</h2>
      <p className="text-sm text-muted mb-8">Manage your profile and organization.</p>

      <div className="grid gap-6">
        {/* Profile Card */}
        <div className="bg-panel border border-border rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-accent" /> User Profile
          </h3>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-accent flex items-center justify-center text-white text-2xl font-bold">
                {user?.email ? user.email[0].toUpperCase() : 'T'}
              </div>
              <div>
                <p className="text-white font-medium text-lg">{user?.email || 'Test User'}</p>
                <p className="text-sm text-muted flex items-center gap-1">
                  <Shield className="w-3 h-3" /> {user?.role || 'Admin'}
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mt-6 border-t border-border pt-6">
              <div>
                <label className="text-xs text-muted mb-1 block">Email Address</label>
                <div className="flex items-center gap-2 bg-background border border-border rounded-lg px-3 py-2">
                  <Mail className="w-4 h-4 text-muted" />
                  <span className="text-sm text-white">{user?.email || 'test@nexora-test.com'}</span>
                </div>
              </div>
              <div>
                <label className="text-xs text-muted mb-1 block">Tenant ID</label>
                <div className="flex items-center gap-2 bg-background border border-border rounded-lg px-3 py-2">
                  <Building className="w-4 h-4 text-muted" />
                  <span className="text-sm text-white font-mono truncate">{user?.tenant_id || 'de2b2f2b-1348...'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Security / Auth */}
        <div className="bg-panel border border-border rounded-xl p-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Key className="w-5 h-5 text-accent" /> Session
            </h3>
            <p className="text-sm text-muted mt-1">You are currently signed in to the Command Center.</p>
          </div>
          <button 
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 bg-danger/10 text-danger border border-danger/20 rounded-lg hover:bg-danger/20 transition-colors"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </div>
    </div>
  )
}
