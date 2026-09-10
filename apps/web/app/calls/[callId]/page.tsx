'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

type Segment = { speaker: string; text: string; started_at: string | null; ended_at: string | null; confidence: number | null }
type Summary = { summary: string; intent: string; outcome: string; sentiment: string; follow_up_required: boolean; next_action: string }
type Action = { id: string; description: string; owner: string | null; due_date: string | null; status: string }
type Intelligence = { call_id: string; transcript: { status: string; segments: Segment[] }; summary: Summary | null; action_items: Action[] }

function formatTime(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString([], { minute: '2-digit', second: '2-digit' })
}

export default function CallIntelligencePage() {
  const params = useParams<{ callId: string }>()
  const callId = params.callId
  const [token, setToken] = useState('')
  const [data, setData] = useState<Intelligence | null>(null)
  const [error, setError] = useState('')
  const [processing, setProcessing] = useState(false)

  async function request(path: string, init: RequestInit = {}) {
    const res = await fetch(`${API}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...(init.headers || {}) },
    })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(body.detail || 'Request failed')
    return body
  }

  async function load() {
    if (!token || !callId) return
    try { setError(''); setData(await request(`/calls/${callId}/intelligence`)) }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to load call intelligence') }
  }

  useEffect(() => { const value = localStorage.getItem('token'); if (value) setToken(value) }, [])
  useEffect(() => { load() }, [token, callId])

  async function processNow() {
    setProcessing(true); setError('')
    try { await request(`/calls/${callId}/intelligence/process`, { method: 'POST' }); await load() }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to process intelligence') }
    finally { setProcessing(false) }
  }

  const summary = data?.summary
  return (
    <main style={{ padding: 32, maxWidth: 1100, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      <p><a href="/calls">← Back to calls</a></p>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <div><div style={{ fontSize: 12, letterSpacing: 2 }}>VOICEOS</div><h1>Call Intelligence</h1><p style={{ color: '#666' }}>Transcript, AI analysis and follow-up actions.</p></div>
        <button onClick={load}>Refresh</button>
      </div>
      {error && <div style={{ padding: 12, margin: '16px 0', border: '1px solid #f0b4b4', borderRadius: 8 }}>{error}</div>}

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, margin: '24px 0' }}>
        {[
          ['Transcript', data?.transcript.status || '—'],
          ['Sentiment', summary?.sentiment || '—'],
          ['Intent', summary?.intent || '—'],
          ['Outcome', summary?.outcome || '—'],
        ].map(([label, value]) => <div key={label} style={{ border: '1px solid #ddd', borderRadius: 10, padding: 16 }}><small>{label}</small><div style={{ marginTop: 8, fontWeight: 700 }}>{value}</div></div>)}
      </section>

      <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><h2 style={{ marginTop: 0 }}>AI Summary</h2>{!summary && <button disabled={processing} onClick={processNow}>{processing ? 'Processing…' : 'Analyze Call'}</button>}</div>
        {summary ? <>
          <p style={{ lineHeight: 1.6 }}>{summary.summary}</p>
          <dl style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 10 }}>
            <dt><strong>Follow-up</strong></dt><dd style={{ margin: 0 }}>{summary.follow_up_required ? 'Required' : 'Not required'}</dd>
            <dt><strong>Next action</strong></dt><dd style={{ margin: 0 }}>{summary.next_action || '—'}</dd>
          </dl>
        </> : <p>No AI analysis is available yet.</p>}
      </section>

      <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 20, marginBottom: 20 }}>
        <h2 style={{ marginTop: 0 }}>Action Items</h2>
        {!data?.action_items.length ? <p>No action items identified.</p> : data.action_items.map(item => <div key={item.id} style={{ padding: '12px 0', borderBottom: '1px solid #eee' }}><strong>{item.description}</strong><div style={{ fontSize: 13, color: '#666', marginTop: 4 }}>{item.owner || 'Unassigned'} · {item.due_date || 'No due date'} · {item.status}</div></div>)}
      </section>

      <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>Transcript</h2>
        {!data?.transcript.segments.length ? <p>No transcript segments captured.</p> : <div>{data.transcript.segments.map((segment, index) => <div key={`${index}-${segment.started_at || ''}`} style={{ padding: '14px 0', borderBottom: '1px solid #eee' }}><div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#666' }}><strong>{segment.speaker}</strong><span>{formatTime(segment.started_at)}</span></div><div style={{ marginTop: 5, lineHeight: 1.55 }}>{segment.text}</div></div>)}</div>}
      </section>
    </main>
  )
}
