'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

type HumanAgent = { id: string; name: string; phone: string; status: string; priority: number; department: string | null }
type Destination = { id: string; name: string; phone: string; routing_group_id: string | null }
type Group = { id: string; name: string; strategy: string }

export default function HandoffPage() {
  const [token, setToken] = useState('')
  const [agents, setAgents] = useState<HumanAgent[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [destinations, setDestinations] = useState<Destination[]>([])
  const [name, setName] = useState(''); const [phone, setPhone] = useState(''); const [status, setStatus] = useState('OFFLINE')
  const [notice, setNotice] = useState(''); const [error, setError] = useState('')
  async function request(path: string, init: RequestInit = {}) { const r=await fetch(`${API}${path}`,{...init,headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`,...(init.headers||{})}}); const d=await r.json().catch(()=>({})); if(!r.ok) throw new Error(d.detail||'Request failed'); return d }
  async function load(){ if(!token)return; try{ const [a,g,d]=await Promise.all([request('/handoff/agents'),request('/handoff/groups'),request('/handoff/destinations')]); setAgents(a);setGroups(g);setDestinations(d);setError('') }catch(e){setError(e instanceof Error?e.message:'Unable to load handoff resources')} }
  useEffect(()=>{const t=localStorage.getItem('token');if(t)setToken(t)},[]); useEffect(()=>{if(token)load()},[token])
  async function addAgent(){if(!name||!phone){setError('Name and phone are required');return}try{await request('/handoff/agents',{method:'POST',body:JSON.stringify({name,phone,status})});setName('');setPhone('');setNotice('Human agent added');load()}catch(e){setError(e instanceof Error?e.message:'Unable to add agent')}}
  return <main style={{padding:32,maxWidth:1100,margin:'0 auto',fontFamily:'system-ui,sans-serif'}}><div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}><div><div style={{fontSize:12,letterSpacing:2}}>VOICEOS</div><h1>Human Handoff</h1><p>Configure human agents and transfer destinations for AI call escalation.</p></div><button onClick={load}>Refresh</button></div>{error&&<div style={{padding:12,border:'1px solid #f0b4b4',borderRadius:8,marginBottom:16}}>{error}</div>}{notice&&<div style={{padding:12,border:'1px solid #b6d7a8',borderRadius:8,marginBottom:16}}>{notice}</div>}<section style={{border:'1px solid #ddd',borderRadius:12,padding:20,marginBottom:24}}><h2>Add human agent</h2><div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr auto',gap:10}}><input placeholder='Name' value={name} onChange={e=>setName(e.target.value)} /><input placeholder='E.164 phone' value={phone} onChange={e=>setPhone(e.target.value)} /><select value={status} onChange={e=>setStatus(e.target.value)}><option>OFFLINE</option><option>AVAILABLE</option><option>ONLINE</option><option>READY</option></select><button onClick={addAgent}>Add</button></div></section><section style={{border:'1px solid #ddd',borderRadius:12,padding:20,marginBottom:24}}><h2>Available agents</h2>{agents.length===0?<p>No human agents configured.</p>:agents.map(a=><div key={a.id} style={{display:'flex',justifyContent:'space-between',padding:'12px 0',borderBottom:'1px solid #eee'}}><span><strong>{a.name}</strong> · {a.phone}</span><span>{a.status}</span></div>)}</section><section style={{border:'1px solid #ddd',borderRadius:12,padding:20}}><h2>Routing configuration</h2><p>{groups.length} routing groups · {destinations.length} transfer destinations</p><p style={{fontSize:13}}>Transfers support Twilio and Plivo provider call legs. Configure destinations through the API until the routing editor is enabled.</p></section></main>
}
