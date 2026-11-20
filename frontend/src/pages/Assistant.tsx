import { useState, useRef, useEffect } from 'react'
import { Bot, Send, User, Sparkles, AlertCircle, CheckCircle2, ChevronRight } from 'lucide-react'

export function Assistant() {
  const [messages, setMessages] = useState<any[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return

    const userMsg = { id: Date.now().toString(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Placeholder for assistant streaming message
    const assistantId = (Date.now() + 1).toString()
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', events: [], final: null, status: 'streaming' }])

    try {
      const token = localStorage.getItem('nexora_token')
      const res = await fetch('/api/v1/orchestrator/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({ user_request: text })
      })

      if (!res.ok) throw new Error('Stream failed')
      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        let frameEnd
        while ((frameEnd = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, frameEnd)
          buffer = buffer.slice(frameEnd + 2)

          for (const line of frame.split('\n')) {
            if (line.startsWith('data: ')) {
              const payload = line.slice(6).trim()
              if (!payload) continue
              try {
                const event = JSON.parse(payload)
                
                // Update the specific assistant message
                setMessages(prev => prev.map(msg => {
                  if (msg.id !== assistantId) return msg

                  if (event.type === 'final') {
                    const state = event.state || {}
                    let content = "Task completed."
                    if (state.status === 'pending_approval') content = "Your request is ready but requires approval before it can execute."
                    else if (state.status === 'failed') content = "The task failed."
                    
                    return { ...msg, status: 'done', final: event, content }
                  } else if (event.type === 'error') {
                    return { ...msg, status: 'error', content: event.error || 'Unknown error' }
                  } else if (event.type === 'end') {
                    return { ...msg, status: msg.status === 'streaming' ? 'done' : msg.status }
                  } else {
                    return { ...msg, events: [...msg.events, event] }
                  }
                }))
              } catch (e) {
                console.warn('Failed to parse SSE', e)
              }
            }
          }
        }
      }
    } catch (err: any) {
      setMessages(prev => prev.map(msg => 
        msg.id === assistantId ? { ...msg, status: 'error', content: err.message } : msg
      ))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-[#0B0F19] max-w-5xl mx-auto border-x border-border">
      
      {/* Header */}
      <div className="p-4 border-b border-border bg-[#111827] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
            <Bot className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Nexora AI Assistant</h2>
            <p className="text-xs text-muted">Agentic workflow orchestrator</p>
          </div>
        </div>
      </div>

      {/* Chat Thread */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-6">
              <Sparkles className="w-8 h-8 text-accent" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">How can I help you today?</h1>
            <p className="text-sm text-muted mb-8">I can orchestrate multi-agent workflows, analyze data, and execute business tasks.</p>
            <div className="grid grid-cols-2 gap-3 w-full">
              {[
                "List my HubSpot leads",
                "Draft a customer support reply",
                "Prepare a monthly sales report",
                "Summarize recent activity"
              ].map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(prompt)}
                  className="p-3 text-left bg-panel border border-border rounded-xl hover:border-accent/50 transition-colors text-sm text-gray-300"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
              msg.role === 'user' ? 'bg-gray-700 text-white' : 'bg-accent text-white'
            }`}>
              {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div className={`max-w-[75%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-accent text-white rounded-tr-sm' 
                  : 'bg-panel border border-border text-gray-200 rounded-tl-sm'
              }`}>
                {msg.role === 'user' ? msg.content : (
                  <>
                    {msg.status === 'streaming' && (
                      <div className="flex items-center gap-2 mb-2 text-muted">
                        <span className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin"></span>
                        Thinking...
                      </div>
                    )}
                    {msg.status === 'error' && (
                      <div className="text-danger flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" /> {msg.content}
                      </div>
                    )}
                    {msg.final && (
                      <div className="space-y-4">
                        <p>{msg.content}</p>
                        {msg.final.state?.tasks && (
                          <div className="mt-4 border-t border-border pt-4">
                            <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Plan Execution</p>
                            <div className="space-y-2">
                              {msg.final.state.tasks.map((task: any, i: number) => {
                                const res = msg.final.state.task_results?.find((r: any) => r.task_id === task.task_id) || {}
                                return (
                                  <div key={i} className="bg-background rounded-lg p-3 border border-border flex items-start gap-3">
                                    <div className="mt-0.5">
                                      {res.status === 'completed' ? <CheckCircle2 className="w-4 h-4 text-success" /> : <ChevronRight className="w-4 h-4 text-warning" />}
                                    </div>
                                    <div>
                                      <p className="text-xs text-white">{task.description}</p>
                                      <p className="text-[10px] text-muted mt-1">Agent: {task.agent_type} • Status: {res.status || 'pending'}</p>
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-[#111827] border-t border-border shrink-0">
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSend(input); }}
          className="relative flex items-center"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Nexora to run a workflow..."
            disabled={loading}
            className="w-full bg-background border border-border rounded-xl pl-4 pr-12 py-3 text-sm text-white focus:outline-none focus:border-accent/50 shadow-sm"
          />
          <button 
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 p-2 bg-accent text-white rounded-lg hover:bg-accentHover disabled:opacity-50 disabled:hover:bg-accent transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        <p className="text-center text-[10px] text-muted mt-2">
          Nexora can make mistakes. Please verify sensitive actions.
        </p>
      </div>
    </div>
  )
}
