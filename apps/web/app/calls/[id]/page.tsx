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

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadCall = useCallback(async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    if (!token) {
      setError('Your session is missing. Sign in and reopen this call.')
      setLoading(false)
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API}/calls?limit=200`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      })
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(typeof payload?.detail === 'string' ? payload.detail : 'Unable to load call records.')
      }
      if (!Array.isArray(payload)) throw new Error('The calls API returned an unexpected response.')
      const match = payload.find((item: Call) => item.id === callId) as Call | undefined
      if (!match) throw new Error('Call not found in the most recent call records.')
      setCall(match)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load this call.')
    } finally {
      setLoading(false)
    }
  }, [callId])

  useEffect(() => { void loadCall() }, [loadCall])

  return (
    <main style={{ maxWidth: 1000, margin: '0 auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <button onClick={() => router.push('/calls')} style={{ marginBottom: 20 }}>← Back to calls</button>
      <header style={{ marginBottom: 24 }}>
        <div style={{ color: '#6b7280', fontSize: 12, letterSpacing: 1.5 }}>CALL INTELLIGENCE</div>
        <h1 style={{ margin: '8px 0' }}>Call details</h1>
        <p style={{ color: '#6b7280', margin: 0 }}>Review the call record and its current outcome.</p>
      </header>

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

          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: 20 }}>
            <h2 style={{ marginTop: 0 }}>Intelligence data</h2>
            <p style={{ color: '#6b7280', marginBottom: 0 }}>
              Transcript, summary, sentiment, extracted actions, and recording details are shown here once the backend exposes them for this call. This page does not invent or infer intelligence data that the API has not returned.
            </p>
          </section>

          <div style={{ marginTop: 16 }}>
            <button onClick={() => void loadCall()}>Refresh details</button>
          </div>
        </>
      )}
    </main>
  )
}
