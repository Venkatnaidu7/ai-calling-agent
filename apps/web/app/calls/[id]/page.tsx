'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

type Call = {
  id: string
  contact_id: string | null
  phone_number_id: string | null
  direction: string
  from_number: string | null
  to_number: string | null
  status: string
  outcome: string | null
  duration_seconds: number | null
  provider_call_id: string | null
  created_at: string
}

type TranscriptSegment = {
  speaker: string | null
  text: string
  started_at: string | null
  ended_at: string | null
  confidence: number | null
}

type ActionItem = {
  id?: string
  description: string
  status?: string
  owner?: string | null
  due_date?: string | null
  created_at?: string | null
}

type Intelligence = {
  call_id: string
  job?: {
    status?: string
    attempts?: number
    last_error?: string | null
    updated_at?: string | null
  } | null
  transcript?: { status?: string; segments?: TranscriptSegment[] }
  summary?: {
    summary?: string | null
    sentiment?: string | null
    intent?: string | null
    outcome?: string | null
    next_action?: string | null
    follow_up_required?: boolean | null
    [key: string]: unknown
  } | null
  action_items?: ActionItem[]
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  return '—'
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 14, minWidth: 0 }}>
      <div style={{ color: '#6b7280', fontSize: 12, marginBottom: 6 }}>{label}</div>
      <div style={{ fontWeight: 600, overflowWrap: 'anywhere' }}>{value ?? '—'}</div>
    </div>
  )
}

export default function CallDetailsPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const callId = params.id
  const [call, setCall] = useState<Call | null>(null)
  const [intelligence, setIntelligence] = useState<Intelligence | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [intelligenceError, setIntelligenceError] = useState('')
  const [notice, setNotice] = useState('')

  const loadCall = useCallback(async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    if (!token) {
      setError('Your session is missing. Sign in and reopen this call.')
      setLoading(false)
      return
    }

    setLoading(true)
    setError('')
    setIntelligenceError('')
    const headers = { Authorization: `Bearer ${token}` }
    try {
      const response = await fetch(`${API}/calls/${encodeURIComponent(callId)}`, { headers, cache: 'no-store' })
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(typeof payload?.detail === 'string' ? payload.detail : 'Unable to load call details.')
      }
      setCall(payload as Call)

      try {
        const intelligenceResponse = await fetch(`${API}/calls/${encodeURIComponent(callId)}/intelligence`, { headers, cache: 'no-store' })
        const intelligencePayload = await intelligenceResponse.json().catch(() => null)
        if (!intelligenceResponse.ok) {
          throw new Error(typeof intelligencePayload?.detail === 'string' ? intelligencePayload.detail : 'Unable to load call intelligence.')
        }
        setIntelligence(intelligencePayload as Intelligence)
      } catch (cause) {
        setIntelligence(null)
        setIntelligenceError(cause instanceof Error ? cause.message : 'Unable to load call intelligence.')
      }
    } catch (cause) {
      setCall(null)
      setIntelligence(null)
      setError(cause instanceof Error ? cause.message : 'Unable to load this call.')
    } finally {
      setLoading(false)
    }
  }, [callId])

  useEffect(() => { void loadCall() }, [loadCall])

  async function processIntelligence() {
    const token = localStorage.getItem('token')
    if (!token) {
      setIntelligenceError('Your session is missing. Sign in and try again.')
      return
    }
    setProcessing(true)
    setIntelligenceError('')
    setNotice('')
    try {
      const response = await fetch(`${API}/calls/${encodeURIComponent(callId)}/intelligence/process`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(typeof payload?.detail === 'string' ? payload.detail : 'Unable to queue intelligence processing.')
      }
      setNotice(`Intelligence processing queued. Status: ${displayValue(payload?.status)}. Use Refresh details to check progress.`)
      await loadCall()
    } catch (cause) {
      setIntelligenceError(cause instanceof Error ? cause.message : 'Unable to queue intelligence processing.')
    } finally {
      setProcessing(false)
    }
  }

  const summary = intelligence?.summary
  const segments = intelligence?.transcript?.segments ?? []
  const actions = intelligence?.action_items ?? []
  const job = intelligence?.job

  return (
    <main style={{ maxWidth: 1000, margin: '0 auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <button onClick={() => router.push('/calls')} style={{ marginBottom: 20 }}>← Back to calls</button>
      <header style={{ marginBottom: 24 }}>
        <div style={{ color: '#6b7280', fontSize: 12, letterSpacing: 1.5 }}>CALL INTELLIGENCE</div>
        <h1 style={{ margin: '8px 0' }}>Call details</h1>
        <p style={{ color: '#6b7280', margin: 0 }}>Review call metadata, transcript, summary, and follow-up actions.</p>
      </header>

      {notice && <p role="status" style={{ border: '1px solid #b6d7a8', borderRadius: 10, padding: 12 }}>{notice}</p>}
      {loading && <p role="status">Loading call details…</p>}
      {!loading && error && (
        <section role="alert" style={{ border: '1px solid #f0b4b4', borderRadius: 10, padding: 16 }}>
          <p style={{ marginTop: 0 }}>{error}</p>
          <button onClick={() => void loadCall()}>Try again</button>
        </section>
      )}

      {!loading && call && (
        <>
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 20 }}>
            <Field label="Status" value={call.status} />
            <Field label="Direction" value={call.direction} />
            <Field label="Outcome" value={call.outcome || 'Not recorded'} />
            <Field label="Duration" value={call.duration_seconds == null ? 'Not recorded' : `${call.duration_seconds} seconds`} />
          </section>

          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: 20, marginBottom: 20 }}>
            <h2 style={{ marginTop: 0 }}>Call information</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
              <Field label="From" value={call.from_number} />
              <Field label="To" value={call.to_number} />
              <Field label="Started" value={formatDate(call.created_at)} />
              <Field label="Call ID" value={call.id} />
              <Field label="Contact ID" value={call.contact_id} />
              <Field label="Phone number ID" value={call.phone_number_id} />
              <Field label="Provider call ID" value={call.provider_call_id} />
            </div>
          </section>

          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: 20, marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <h2 style={{ marginTop: 0 }}>Call intelligence</h2>
              <button onClick={processIntelligence} disabled={processing}>
                {processing ? 'Queueing…' : 'Process intelligence'}
              </button>
            </div>
            {intelligenceError && <p role="alert" style={{ color: '#b91c1c' }}>{intelligenceError}</p>}
            {intelligence && (
              <>
                <p><strong>Processing status:</strong> {job?.status || 'NOT_QUEUED'} · <strong>Attempts:</strong> {job?.attempts ?? 0}</p>
                {job?.last_error && <p role="alert" style={{ color: '#b91c1c' }}>Last processing error: {job.last_error}</p>}
                <p><strong>Transcript status:</strong> {intelligence.transcript?.status || 'NOT_STARTED'}</p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
                  <Field label="Intent" value={displayValue(summary?.intent)} />
                  <Field label="Sentiment" value={displayValue(summary?.sentiment)} />
                  <Field label="Detected outcome" value={displayValue(summary?.outcome)} />
                  <Field label="Next action" value={displayValue(summary?.next_action)} />
                  <Field label="Follow-up required" value={displayValue(summary?.follow_up_required)} />
                </div>
                <h3>Summary</h3>
                <p style={{ whiteSpace: 'pre-wrap' }}>{displayValue(summary?.summary)}</p>

                <h3>Transcript</h3>
                {segments.length === 0 ? <p>No transcript segments are available yet.</p> : (
                  <ol style={{ paddingLeft: 24 }}>
                    {segments.map((segment, index) => (
                      <li key={`${segment.started_at || 'segment'}-${index}`} style={{ marginBottom: 12 }}>
                        <div style={{ color: '#6b7280', fontSize: 12 }}>
                          {displayValue(segment.speaker)} · {formatDate(segment.started_at)}
                        </div>
                        <div style={{ whiteSpace: 'pre-wrap' }}>{segment.text}</div>
                      </li>
                    ))}
                  </ol>
                )}

                <h3>Action items</h3>
                {actions.length === 0 ? <p>No follow-up actions are recorded yet.</p> : (
                  <ul>
                    {actions.map((item, index) => (
                      <li key={item.id || `${item.description || 'action'}-${index}`} style={{ marginBottom: 10 }}>
                        <strong>{item.description}</strong>
                        <div style={{ color: '#6b7280', fontSize: 12 }}>
                          {item.owner ? `Owner: ${item.owner} · ` : ''}{item.status || 'OPEN'}{item.due_date ? ` · Due ${item.due_date}` : ''}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </section>

          <button onClick={() => void loadCall()}>Refresh details</button>
        </>
      )}
    </main>
  )
}
