'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
type Agent = { id: string; name: string; active_version_id: string | null }
type Phone = { id: string; e164: string; provider: string; provider_number_id: string | null; country: string | null; agent_id: string | null; inbound_enabled: boolean; outbound_enabled: boolean; active: boolean }
type Available = { phone_number: string; friendly_name?: string; locality?: string; region?: string; provider: string; monthly_rental_rate?: string }

export default function PhoneNumbersPage() {
  const [token, setToken] = useState('')
  const [phones, setPhones] = useState<Phone[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [provider, setProvider] = useState<'twilio' | 'plivo'>('plivo')
  const [country, setCountry] = useState('IN')
  const [areaCode, setAreaCode] = useState('')
  const [available, setAvailable] = useState<Available[]>([])
  const [number, setNumber] = useState('')
  const [agentId, setAgentId] = useState('')
  const [inbound, setInbound] = useState(true)
  const [outbound, setOutbound] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function request(path: string, init: RequestInit = {}) {
    const headers = new Headers(init.headers)
    headers.set('Authorization', `Bearer ${token}`)
    if (init.body) headers.set('Content-Type', 'application/json')
    const response = await fetch(API + path, { ...init, headers })
    const body = await response.json().catch(() => null)
    if (!response.ok) throw new Error(body?.detail || 'Request failed')
    return body
  }

  async function load() {
    if (!token) return
    const [p, a] = await Promise.all([request('/phone-numbers'), request('/agents')])
    setPhones(p); setAgents(a)
  }

  useEffect(() => {
    const stored = localStorage.getItem('token')
    if (stored) setToken(stored)
  }, [])

  useEffect(() => { if (token) load().catch(e => setError(e.message)) }, [token])

  async function searchNumbers() {
    setBusy(true); setError(''); setMessage('')
    try {
      const params = new URLSearchParams({ provider, country, limit: '20' })
      if (areaCode.trim()) params.set('area_code', areaCode.trim())
      setAvailable(await request(`/phone-numbers/available?${params.toString()}`))
    } catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }

  async function provision(selected?: string) {
    const chosen = selected || number
    if (!chosen) return setError('Select or enter a phone number first')
    setBusy(true); setError(''); setMessage('')
    try {
      const path = provider === 'plivo' ? '/phone-numbers/plivo/attach' : '/phone-numbers/provision'
      const body = { phone_number: chosen, ...(provider === 'twilio' ? { provider: 'twilio' } : {}), agent_id: agentId || null, country, inbound_enabled: inbound, outbound_enabled: outbound }
      await request(path, { method: 'POST', body: JSON.stringify(body) })
      setNumber(''); setAvailable([]); setMessage(`${provider.toUpperCase()} number configured successfully.`); await load()
    } catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }

  async function toggle(id: string, field: string, value: boolean) {
    setBusy(true); setError('')
    try { await request(`/phone-numbers/${id}`, { method: 'PATCH', body: JSON.stringify({ [field]: value }) }); await load() }
    catch (e: any) { setError(e.message) } finally { setBusy(false) }
  }

  if (!token) return <main className="login"><div className="card"><h1>Phone Numbers</h1><p>Sign in from the main VoiceOS workspace first.</p></div></main>

  return <main className="content" style={{ maxWidth: 1100, margin: '0 auto', padding: 32 }}>
    <header><div><div className="eyebrow">VOICE INFRASTRUCTURE</div><h1>Phone Numbers</h1></div><span className="pill">Twilio + Plivo only</span></header>
    {message && <div className="card" style={{ marginBottom: 16 }}>{message}</div>}
    {error && <div className="card" style={{ marginBottom: 16 }}>{error}</div>}

    <section className="card">
      <h2>Configure provider number</h2>
      <p>Plivo can attach a number you already own. Twilio/Plivo provisioning remains provider-controlled.</p>
      <div style={{ display: 'grid', gap: 12, marginTop: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <label>Provider<select value={provider} onChange={e => { setProvider(e.target.value as 'twilio' | 'plivo'); setAvailable([]) }}><option value="plivo">Plivo</option><option value="twilio">Twilio</option></select></label>
          <label>Country<input value={country} onChange={e => setCountry(e.target.value.toUpperCase())} maxLength={4} placeholder="IN" /></label>
        </div>
        <label>Phone number<input value={number} onChange={e => setNumber(e.target.value)} placeholder="E.164, e.g. +919876543210" /></label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <label>AI Agent<select value={agentId} onChange={e => setAgentId(e.target.value)}><option value="">No AI agent assigned</option>{agents.map(a => <option key={a.id} value={a.id}>{a.name}{a.active_version_id ? ' · Published' : ' · Draft'}</option>)}</select></label>
          <label>Area code for search<input value={areaCode} onChange={e => setAreaCode(e.target.value)} placeholder="Optional" /></label>
        </div>
        <div style={{ display: 'flex', gap: 20 }}><label><input type="checkbox" checked={inbound} onChange={e => setInbound(e.target.checked)} /> Inbound</label><label><input type="checkbox" checked={outbound} onChange={e => setOutbound(e.target.checked)} /> Outbound</label></div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}><button disabled={busy} onClick={searchNumbers}>{busy ? 'Working…' : 'Search available numbers'}</button><button disabled={busy || !number} onClick={() => provision()}>{busy ? 'Working…' : `Configure ${provider.toUpperCase()} number`}</button></div>
      </div>
    </section>

    {available.length > 0 && <section className="card" style={{ marginTop: 16 }}><h2>Available {provider.toUpperCase()} numbers</h2><div style={{ display: 'grid', gap: 10, marginTop: 12 }}>{available.map(n => <div key={n.phone_number} style={{ border: '1px solid #ddd', borderRadius: 10, padding: 14, display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center' }}><div><strong>{n.phone_number}</strong><div>{n.locality || n.friendly_name || ''} {n.region || ''}{n.monthly_rental_rate ? ` · ${n.monthly_rental_rate}/month` : ''}</div></div><button disabled={busy} onClick={() => provision(n.phone_number)}>Use this number</button></div>)}</div></section>}

    <section className="card" style={{ marginTop: 16 }}><h2>Configured numbers</h2>{phones.length === 0 ? <p>No numbers configured.</p> : phones.map(p => <div key={p.id} style={{ border: '1px solid #ddd', borderRadius: 10, padding: 16, marginTop: 10 }}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}><div><strong>{p.e164}</strong><div>{p.provider.toUpperCase()} · {p.country || 'Unknown country'} · {p.agent_id ? agents.find(a => a.id === p.agent_id)?.name || 'Assigned agent' : 'No agent assigned'}</div><small>Provider ID: {p.provider_number_id || 'Not available'}</small></div><span className="pill">{p.active ? 'Active' : 'Disabled'}</span></div><div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap' }}><button disabled={busy} onClick={() => toggle(p.id, 'active', !p.active)}>{p.active ? 'Disable' : 'Enable'}</button><button disabled={busy} onClick={() => toggle(p.id, 'inbound_enabled', !p.inbound_enabled)}>{p.inbound_enabled ? 'Disable inbound' : 'Enable inbound'}</button><button disabled={busy} onClick={() => toggle(p.id, 'outbound_enabled', !p.outbound_enabled)}>{p.outbound_enabled ? 'Disable outbound' : 'Enable outbound'}</button></div></div>)}</section>
  </main>
}
