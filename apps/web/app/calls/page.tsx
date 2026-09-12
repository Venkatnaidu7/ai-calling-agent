'use client'

import { useEffect, useMemo, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1'

type Contact = { id: string; first_name: string; last_name: string; phone: string | null; email: string | null; status: string }
type Agent = { id: string; name: string; description: string | null; active_version_id: string | null; active: boolean }
type Phone = { id: string; e164: string; provider: string; agent_id: string | null; inbound_enabled: boolean; outbound_enabled: boolean; active: boolean }
type Call = { id: string; contact_id: string | null; phone_number_id: string | null; direction: string; from_number: string | null; to_number: string | null; status: string; outcome: string | null; duration_seconds: number | null; provider_call_id: string | null; created_at: string }

const activeStatuses = new Set(['QUEUED', 'RINGING', 'IN_PROGRESS'])

export default function CallsConsole() {
  const [token, setToken] = useState('')
  const [calls, setCalls] = useState<Call[]>([])
  const [summary, setSummary] = useState<Record<string, number>>({})
  const [contacts, setContacts] = useState<Contact[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [phones, setPhones] = useState<Phone[]>([])
  const [contactId, setContactId] = useState('')
  const [agentId, setAgentId] = useState('')
  const [phoneId, setPhoneId] = useState('')
  const [status, setStatus] = useState('')
  const [direction, setDirection] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [calling, setCalling] = useState(false)

  const selectedContact = contacts.find(c => c.id === contactId)
  const availablePhones = useMemo(() => phones.filter(p => p.active && p.outbound_enabled && (!agentId || p.agent_id === agentId)), [phones, agentId])

  async function request(path: string, init: RequestInit = {}) {
    const res = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...(init.headers || {}) } })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || 'Request failed')
    return data
  }

  async function loadCalls() {
    if (!token) return
    try {
      setError('')
      const qs = new URLSearchParams()
      if (status) qs.set('status', status)
      if (direction) qs.set('direction', direction)
      const [a, b] = await Promise.all([request(`/calls?${qs}`), request('/calls/summary')])
      setCalls(a); setSummary(b)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load calls') }
  }

  async function loadResources() {
    if (!token) return
    try {
      const [c, a, p] = await Promise.all([request('/contacts?limit=200'), request('/agents'), request('/phone-numbers')])
      setContacts(c); setAgents(a); setPhones(p)
      const firstAgent = a.find((x: Agent) => x.active && x.active_version_id)
      if (!agentId && firstAgent) setAgentId(firstAgent.id)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load calling resources') }
  }

  useEffect(() => { const t = localStorage.getItem('token'); if (t) setToken(t) }, [])
  useEffect(() => { if (token) { loadCalls(); loadResources() } }, [token])
  useEffect(() => { loadCalls() }, [status, direction])
  useEffect(() => { if (!phoneId || !availablePhones.some(p => p.id === phoneId)) setPhoneId(availablePhones[0]?.id || '') }, [agentId, availablePhones])
  useEffect(() => { const timer = setInterval(() => { if (token) loadCalls() }, 3000); return () => clearInterval(timer) }, [token, status, direction])

  async function startCall() {
    if (!contactId || !phoneId) { setError('Select a contact and an AI phone number before calling'); return }
    setCalling(true); setError(''); setNotice('')
    try { const result = await request(`/calls/outbound?contact_id=${encodeURIComponent(contactId)}&phone_number_id=${encodeURIComponent(phoneId)}`, { method: 'POST' }); setNotice(`Call started: ${result.status}`); await loadCalls() }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to start call') }
    finally { setCalling(false) }
  }

  async function hangup(callId: string) {
    try { await request(`/calls/${callId}/hangup`, { method: 'POST' }); setNotice('Call ended'); await loadCalls() }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to end call') }
  }

  function contactLabel(c: Contact) { return `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.phone || c.email || c.id }

  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <div><div style={{ fontSize: 12, letterSpacing: 2 }}>VOICEOS</div><h1 style={{ marginBottom: 4 }}>Calling Console</h1><p style={{ marginTop: 0 }}>Start, monitor and control AI phone calls.</p></div>
        <button onClick={() => { loadCalls(); loadResources() }}>Refresh</button>
      </div>

      {error && <div style={{ padding: 12, marginBottom: 16, border: '1px solid #f0b4b4', borderRadius: 8 }}>{error}</div>}
      {notice && <div style={{ padding: 12, marginBottom: 16, border: '1px solid #b6d7a8', borderRadius: 8 }}>{notice}</div>}

      <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 20, marginBottom: 24 }}>
        <h2 style={{ marginTop: 0 }}>Make an outbound call</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          <label>Contact<select value={contactId} onChange={e => setContactId(e.target.value)} style={{ display: 'block', width: '100%', padding: 10, marginTop: 6 }}><option value="">Select contact</option>{contacts.filter(c => c.phone && c.status !== 'DELETED').map(c => <option key={c.id} value={c.id}>{contactLabel(c)} — {c.phone}</option>)}</select></label>
          <label>AI Agent<select value={agentId} onChange={e => setAgentId(e.target.value)} style={{ display: 'block', width: '100%', padding: 10, marginTop: 6 }}><option value="">Select agent</option>{agents.filter(a => a.active && a.active_version_id).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
          <label>Calling number<select value={phoneId} onChange={e => setPhoneId(e.target.value)} style={{ display: 'block', width: '100%', padding: 10, marginTop: 6 }}><option value="">Select phone</option>{availablePhones.map(p => <option key={p.id} value={p.id}>{p.e164}</option>)}</select></label>
        </div>
        {selectedContact && <p style={{ fontSize: 13 }}>Destination: <strong>{selectedContact.phone}</strong></p>}
        <button disabled={calling || !contactId || !phoneId} onClick={startCall} style={{ marginTop: 8, padding: '11px 20px', fontWeight: 700 }}>{calling ? 'Starting call…' : '📞 Call Now'}</button>
        {agentId && availablePhones.length === 0 && <p style={{ fontSize: 13 }}>No active outbound phone number is assigned to this agent.</p>}
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>{[['Total', summary.total || 0], ['Active', summary.active || 0], ['Completed', summary.completed || 0], ['Failed', summary.failed || 0]].map(([k, v]) => <div key={k as string} style={{ border: '1px solid #ddd', borderRadius: 10, padding: 16 }}><small>{k}</small><h2 style={{ marginBottom: 0 }}>{v}</h2></div>)}</div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}><select value={status} onChange={e => setStatus(e.target.value)}><option value="">All statuses</option>{['QUEUED','RINGING','IN_PROGRESS','COMPLETED','FAILED','NO_ANSWER','BUSY'].map(x => <option key={x}>{x}</option>)}</select><select value={direction} onChange={e => setDirection(e.target.value)}><option value="">All directions</option><option>INBOUND</option><option>OUTBOUND</option></select></div>

      <section style={{ border: '1px solid #ddd', borderRadius: 12, overflow: 'hidden' }}>
        {calls.length === 0 ? <p style={{ padding: 20 }}>No calls found.</p> : calls.map(c => <div key={c.id} style={{ padding: 16, borderBottom: '1px solid #eee', display: 'grid', gridTemplateColumns: '1.2fr .8fr .8fr 1fr auto auto', gap: 12, alignItems: 'center' }}><div><strong>{c.to_number || c.from_number || 'Unknown number'}</strong><div><small>{c.direction} · {new Date(c.created_at).toLocaleString()}</small></div></div><span>{c.status}</span><span>{c.duration_seconds != null ? `${c.duration_seconds}s` : '—'}</span><span>{c.outcome || c.provider_call_id || '—'}</span><a href={`/calls/${c.id}`} style={{ fontWeight: 600 }}>Details</a>{activeStatuses.has(c.status) ? <button onClick={() => hangup(c.id)}>Hang Up</button> : <span />}</div>)}
      </section>
    </main>
  )
}
