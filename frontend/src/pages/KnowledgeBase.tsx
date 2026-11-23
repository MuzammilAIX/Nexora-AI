import { useState, useEffect, useMemo, useRef } from 'react'
import {
  FileText, Upload, Search, Trash2, X, Loader2, AlertCircle,
  FileType, FolderOpen, Download, CheckCircle2, Clock, Tag
} from 'lucide-react'

interface Document {
  id: string
  filename: string
  file_type: string
  size_bytes: number
  category: string
  processing_status: string
  chunk_count: number
  uploaded_at: string
  has_text?: boolean
  text_length?: number
}

interface DocumentDetail extends Document {
  extracted_text: string
  error_message?: string | null
}

const CATEGORY_COLORS: Record<string, string> = {
  policy: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  procedure: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  faq: 'bg-green-500/10 text-green-400 border-green-500/30',
  product: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  test: 'bg-panelHover text-muted border-border',
  uncategorized: 'bg-panelHover text-muted border-border',
}

const STATUS_COLORS: Record<string, string> = {
  ready: 'bg-success/10 text-success border-success/20',
  processing: 'bg-warning/10 text-warning border-warning/20',
  failed: 'bg-danger/10 text-danger border-danger/20',
  uploaded: 'bg-accent/10 text-accent border-accent/20',
}

const FILE_TYPE_ICONS: Record<string, string> = {
  pdf: '📄',
  docx: '📝',
  txt: '📃',
  csv: '📊',
  md: '📋',
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 60000) return 'just now'
  const min = Math.floor(ms / 60000)
  if (min < 60) return min + 'm ago'
  const h = Math.floor(min / 60)
  if (h < 24) return h + 'h ago'
  return Math.floor(h / 24) + 'd ago'
}
export function KnowledgeBase() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [detail, setDetail] = useState<DocumentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadCategory, setUploadCategory] = useState('uncategorized')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const token = () => localStorage.getItem('nexora_token')
  const authHeaders = () => ({ Authorization: 'Bearer ' + token() })

  async function fetchDocuments() {
    try {
      const res = await fetch('/api/v1/documents', { headers: authHeaders() })
      if (!res.ok) throw new Error('Failed to load documents')
      const data = await res.json()
      setDocuments(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [])

  async function handleUpload() {
    if (!uploadFile) return
    setUploading(true)
    setUploadError(null)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('category', uploadCategory)

      const res = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        headers: authHeaders(),
        body: formData,
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Upload failed (${res.status})`)
      }

      setShowUpload(false)
      setUploadFile(null)
      setUploadCategory('uncategorized')
      if (fileInputRef.current) fileInputRef.current.value = ''
      await fetchDocuments()
    } catch (e: any) {
      setUploadError(e.message)
    } finally {
      setUploading(false)
    }
  }

  async function openDetail(doc: Document) {
    setDetailLoading(true)
    setDetail({ ...doc, extracted_text: '' })
    try {
      const res = await fetch(`/api/v1/documents/${doc.id}`, { headers: authHeaders() })
      if (res.ok) {
        const full = await res.json()
        setDetail(full)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setDetailLoading(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this document? This cannot be undone.')) return
    setDeleting(id)
    try {
      const res = await fetch(`/api/v1/documents/${id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (!res.ok) throw new Error('Delete failed')
      await fetchDocuments()
      if (detail?.id === id) setDetail(null)
    } catch (e: any) {
      alert(e.message)
    } finally {
      setDeleting(null)
    }
  }

  const categories = useMemo(() => {
    const set = new Set(documents.map(d => d.category || 'uncategorized'))
    return ['all', ...Array.from(set).sort()]
  }, [documents])

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    return documents.filter(d => {
      if (categoryFilter !== 'all' && (d.category || 'uncategorized') !== categoryFilter) return false
      if (q && !d.filename.toLowerCase().includes(q)) return false
      return true
    })
  }, [documents, search, categoryFilter])

  const totalText = documents.reduce((sum, d) => sum + (d.text_length || 0), 0)
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Knowledge Base</h1>
          <p className="text-sm text-muted">
            {loading ? 'Loading...' : `${documents.length} document${documents.length === 1 ? '' : 's'} · ${(totalText / 1000).toFixed(1)}k chars extracted`}
          </p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-accentHover flex items-center gap-2"
        >
          <Upload className="w-4 h-4" /> Upload Document
        </button>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Documents', value: documents.length, icon: FileText, color: 'text-accent' },
          { label: 'Ready', value: documents.filter(d => d.processing_status === 'ready').length, icon: CheckCircle2, color: 'text-success' },
          { label: 'Processing', value: documents.filter(d => d.processing_status === 'processing').length, icon: Clock, color: 'text-warning' },
          { label: 'Categories', value: categories.length - 1, icon: Tag, color: 'text-purple-400' },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-background border border-border rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted mb-1">{kpi.label}</p>
              <p className="text-2xl font-bold text-white">{loading ? '…' : kpi.value}</p>
            </div>
            <kpi.icon className={`w-6 h-6 ${kpi.color}`} />
          </div>
        ))}
      </div>

      <div className="bg-background border border-border rounded-xl p-4 mb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search documents by filename..."
            className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-white"
        >
          {categories.map(c => <option key={c} value={c}>{c === 'all' ? 'All categories' : c}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="bg-background border border-border rounded-xl p-5 animate-pulse">
              <div className="h-8 w-8 bg-border rounded mb-3"></div>
              <div className="h-3 bg-border rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-border rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-background border border-border rounded-xl p-12 text-center">
          <FolderOpen className="w-12 h-12 text-muted mx-auto mb-3 opacity-40" />
          <p className="text-sm text-white mb-1">{documents.length === 0 ? 'No documents yet' : 'No documents match your filter'}</p>
          <p className="text-xs text-muted mb-4">{documents.length === 0 ? 'Upload company policies, FAQs, or product docs so agents can use them.' : 'Try clearing the search or category filter.'}</p>
          {documents.length === 0 && (
            <button onClick={() => setShowUpload(true)} className="bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-accentHover">
              Upload First Document
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {filtered.map((doc) => (
            <div key={doc.id} className="bg-background border border-border rounded-xl p-5 hover:border-accent/40 transition-colors group cursor-pointer" onClick={() => openDetail(doc)}>
              <div className="flex items-start justify-between mb-3">
                <div className="text-3xl">{FILE_TYPE_ICONS[doc.file_type] || '📄'}</div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(doc.id) }}
                  disabled={deleting === doc.id}
                  className="text-muted hover:text-danger opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50 p-1"
                >
                  {deleting === doc.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                </button>
              </div>
              <h3 className="text-sm font-medium text-white truncate mb-1" title={doc.filename}>{doc.filename}</h3>
              <p className="text-xs text-muted mb-3">{formatBytes(doc.size_bytes)} · {relativeTime(doc.uploaded_at)}</p>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[10px] px-2 py-0.5 rounded border ${CATEGORY_COLORS[doc.category] || CATEGORY_COLORS.uncategorized}`}>
                  {doc.category || 'uncategorized'}
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded border ${STATUS_COLORS[doc.processing_status] || STATUS_COLORS.uploaded}`}>
                  {doc.processing_status}
                </span>
              </div>
              {doc.text_length && (
                <p className="text-[10px] text-muted mt-2">{(doc.text_length / 1000).toFixed(1)}k chars · {doc.chunk_count} chunks</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => !uploading && setShowUpload(false)}>
          <div className="bg-background border border-border rounded-xl max-w-lg w-full p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-semibold text-white">Upload Document</h3>
              <button onClick={() => !uploading && setShowUpload(false)} className="text-muted hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-muted mb-4">
              Supported: <span className="text-white font-mono">.txt · .csv · .md · .pdf · .docx</span> (max 10 MB)
            </p>

            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.csv,.md,.pdf,.docx"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              disabled={uploading}
              className="w-full bg-background border border-border rounded-lg p-3 text-sm text-white file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-accent file:text-white file:text-xs file:font-medium hover:file:bg-accentHover disabled:opacity-50"
            />

            <div className="mt-4">
              <label className="block text-xs text-muted mb-1">Category</label>
              <select
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value)}
                disabled={uploading}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white disabled:opacity-50"
              >
                <option value="uncategorized">Uncategorized</option>
                <option value="policy">Policy</option>
                <option value="procedure">Procedure</option>
                <option value="faq">FAQ</option>
                <option value="product">Product</option>
                <option value="test">Test</option>
              </select>
            </div>

            {uploadError && (
              <div className="mt-4 bg-danger/10 border border-danger/30 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-danger shrink-0 mt-0.5" />
                <p className="text-xs text-danger">{uploadError}</p>
              </div>
            )}

            <div className="flex gap-2 mt-6">
              <button
                onClick={handleUpload}
                disabled={!uploadFile || uploading}
                className="flex-1 bg-accent text-white py-2 rounded-lg text-sm font-medium hover:bg-accentHover disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {uploading ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</> : <><Upload className="w-4 h-4" /> Upload</>}
              </button>
              <button
                onClick={() => setShowUpload(false)}
                disabled={uploading}
                className="px-4 bg-background border border-border text-white py-2 rounded-lg text-sm font-medium hover:bg-panelHover disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setDetail(null)}>
          <div className="bg-background border border-border rounded-xl max-w-3xl w-full max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-border flex items-start justify-between shrink-0">
              <div>
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <span className="text-2xl">{FILE_TYPE_ICONS[detail.file_type] || '📄'}</span>
                  {detail.filename}
                </h3>
                <p className="text-xs text-muted mt-1">{formatBytes(detail.size_bytes)} · uploaded {relativeTime(detail.uploaded_at)}</p>
              </div>
              <button onClick={() => setDetail(null)} className="text-muted hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-background border border-border rounded-lg p-3">
                  <p className="text-[10px] text-muted uppercase mb-1">Type</p>
                  <p className="text-sm text-white uppercase font-mono">{detail.file_type}</p>
                </div>
                <div className="bg-background border border-border rounded-lg p-3">
                  <p className="text-[10px] text-muted uppercase mb-1">Category</p>
                  <p className="text-sm text-white capitalize">{detail.category || 'uncategorized'}</p>
                </div>
                <div className="bg-background border border-border rounded-lg p-3">
                  <p className="text-[10px] text-muted uppercase mb-1">Status</p>
                  <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_COLORS[detail.processing_status] || STATUS_COLORS.uploaded}`}>
                    {detail.processing_status}
                  </span>
                </div>
              </div>

              <div>
                <p className="text-xs uppercase text-muted mb-2">Extracted Text ({((detail.extracted_text || '').length / 1000).toFixed(1)}k chars, {detail.chunk_count} chunks)</p>
                {detailLoading ? (
                  <div className="text-center text-sm text-muted py-6">
                    <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> Loading text...
                  </div>
                ) : detail.extracted_text ? (
                  <pre className="p-4 bg-background border border-border rounded-lg text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto max-h-96">
{detail.extracted_text}
                  </pre>
                ) : (
                  <div className="p-6 bg-background border border-border rounded-lg text-center text-sm text-muted">
                    No text extracted yet — processing may still be underway, or extraction requires additional dependencies.
                  </div>
                )}
              </div>

              {detail.error_message && (
                <div className="bg-danger/10 border border-danger/30 rounded-lg p-3">
                  <p className="text-xs text-danger">{detail.error_message}</p>
                </div>
              )}
            </div>
            <div className="px-6 py-3 border-t border-border flex gap-2 shrink-0">
              <button
                onClick={() => handleDelete(detail.id)}
                disabled={deleting === detail.id}
                className="bg-danger/10 text-danger border border-danger/30 px-4 py-2 rounded-lg text-sm font-medium hover:bg-danger/20 disabled:opacity-50 flex items-center gap-2"
              >
                {deleting === detail.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Delete
              </button>
              <div className="flex-1" />
              <button onClick={() => setDetail(null)} className="bg-background border border-border text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-panelHover">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}