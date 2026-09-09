'use client'

import {useEffect,useState} from 'react'

const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000/api/v1'

type Agent={id:string;tenant_id:string;name:string;description:string|null;active_version_id:string|null;active:boolean}

export default function Home(){
 const [token,setToken]=useState(''); const [tab,setTab]=useState('Dashboard'); const [data,setData]=useState<any>(null)
 const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [error,setError]=useState('');
 const [agents,setAgents]=useState<Agent[]>([]); const [showCreate,setShowCreate]=useState(false); const [saving,setSaving]=useState(false); const [message,setMessage]=useState('')
 const [form,setForm]=useState({name:'',description:'',greeting:'Hello! How can I help you today?',system_instructions:'',voice:'marin',language:'en',personality:'professional, warm',business_context:'',objectives:'',transfer_rules:'',compliance:''})

 async function login(e:any){e.preventDefault();setError('');let r=await fetch(API+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});let j=await r.json();if(!r.ok){setError(j.detail||'Login failed');return}localStorage.setItem('token',j.access_token);setToken(j.access_token)}
 async function load(path:string){let r=await fetch(API+path,{headers:{Authorization:`Bearer ${token}`}});let j=await r.json();if(!r.ok){setError(j.detail||'Request failed');return null}setData(j);return j}
 async function loadAgents(){let j=await load('/agents');if(j)setAgents(j)}
 useEffect(()=>{const t=localStorage.getItem('token');if(t)setToken(t)},[])
 useEffect(()=>{if(!token)return;if(tab==='Dashboard')load('/analytics/summary?days=7');if(tab==='AI Agents')loadAgents();if(tab==='Calls')load('/calls');if(tab==='Contacts')load('/contacts');if(tab==='Appointments')load('/appointments');if(tab==='Campaigns')load('/campaigns')},[token,tab])
 async function createAgent(e:any){e.preventDefault();setSaving(true);setError('');setMessage('');try{
   const r=await fetch(API+'/agents',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:JSON.stringify({name:form.name,description:form.description||null})});
   const a=await r.json(); if(!r.ok)throw new Error(a.detail||'Could not create agent')
   const objectives=form.objectives.split('\n').map(x=>x.trim()).filter(Boolean)
   let transfer_rules={}; let compliance={}; try{if(form.transfer_rules.trim())transfer_rules=JSON.parse(form.transfer_rules);if(form.compliance.trim())compliance=JSON.parse(form.compliance)}catch{throw new Error('Transfer rules and compliance must be valid JSON')}
   const vr=await fetch(API+`/agents/${a.id}/versions`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:JSON.stringify({greeting:form.greeting,system_instructions:form.system_instructions,voice:form.voice,language:form.language,personality:form.personality,business_context:form.business_context||null,objectives,transfer_rules,compliance})});
   const v=await vr.json(); if(!vr.ok)throw new Error(v.detail||'Agent created but version creation failed')
   const pr=await fetch(API+`/agents/${a.id}/versions/${v.id}/publish`,{method:'POST',headers:{Authorization:`Bearer ${token}`}});const p=await pr.json();if(!pr.ok)throw new Error(p.detail||'Agent created but publishing failed')
   setShowCreate(false);setForm({name:'',description:'',greeting:'Hello! How can I help you today?',system_instructions:'',voice:'marin',language:'en',personality:'professional, warm',business_context:'',objectives:'',transfer_rules:'',compliance:''});setMessage('AI agent created and published successfully.');await loadAgents()
 }catch(err:any){setError(err.message)}finally{setSaving(false)}}

 if(!token)return <main className="login"><div className="card"><div className="eyebrow">AI VOICE EMPLOYEE</div><h1>Give your business a voice.</h1><p>Production-oriented AI calling platform for inbound and authorized outbound conversations.</p><form onSubmit={login}><input value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email" type="email"/><input value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" type="password"/><button>Sign in</button></form><small>{error||'Use your configured tenant account.'}</small></div></main>
 const nav=['Dashboard','AI Agents','Phone Numbers','Calls','Contacts','Campaigns','Appointments','Knowledge','Human Agents','Analytics','Billing','Team','Audit Logs','Settings'];
 return <div className="app"><aside><div className="brand">◉ VoiceOS</div>{nav.map(x=><button className={tab===x?'active':''} onClick={()=>{setTab(x);setError('');setMessage('')}} key={x}>{x}</button>)}<button onClick={()=>{localStorage.removeItem('token');setToken('')}} className="logout">Sign out</button></aside><main className="content"><header><div><div className="eyebrow">WORKSPACE</div><h1>{tab}</h1></div><span className="pill">Production foundation</span></header>
 {message&&<div className="card" style={{marginBottom:16}}>{message}</div>}{error&&<div className="card" style={{marginBottom:16}}>{error}</div>}
 {tab==='Dashboard'?<><section className="hero"><div><h2>Your AI employees are ready to work.</h2><p>Connect a Twilio number, publish an agent, and the realtime voice pipeline can answer calls.</p></div><div className="hero-stat"><b>{data?.total_calls??0}</b><span>calls · last 7 days</span></div></section><div className="grid">{[['Answered',data?.answered??0],['Completed',data?.completed??0],['Avg duration',`${Math.round(data?.average_duration_seconds??0)}s`],['Transfer rate',`${Math.round((data?.transfer_rate??0)*100)}%`]].map(([a,b])=><div className="metric" key={a as string}><span>{a}</span><strong>{b}</strong></div>)}</div></>:
 tab==='AI Agents'?<section className="card"><div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:16,marginBottom:20}}><div><h2 style={{margin:'0 0 6px'}}>AI Agents</h2><p style={{margin:0}}>Create, configure and publish the AI employees used by your calling workflows.</p></div><button onClick={()=>{setShowCreate(true);setError('');setMessage('')}}>+ Create AI Agent</button></div>
 {agents.length===0?<div style={{padding:'30px 0'}}><strong>No AI agents yet.</strong><p>Create your first agent to continue to phone and calling setup.</p></div>:<div style={{display:'grid',gap:12}}>{agents.map(a=><div key={a.id} style={{border:'1px solid #ddd',borderRadius:10,padding:16,display:'flex',justifyContent:'space-between',gap:16,alignItems:'center'}}><div><strong>{a.name}</strong><div>{a.description||'No description'}</div></div><span className="pill">{a.active_version_id?'Published':'Draft'}</span></div>)}</div>}
 {showCreate&&<div style={{marginTop:24,paddingTop:24,borderTop:'1px solid #ddd'}}><h2>Create AI Agent</h2><form onSubmit={createAgent} style={{display:'grid',gap:12,maxWidth:760}}>
 <input required value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder="Agent name"/><input value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Description"/>
 <input required value={form.greeting} onChange={e=>setForm({...form,greeting:e.target.value})} placeholder="Greeting"/>
 <textarea required value={form.system_instructions} onChange={e=>setForm({...form,system_instructions:e.target.value})} placeholder="System instructions: what should this AI employee do?" rows={7}/>
 <textarea value={form.business_context} onChange={e=>setForm({...form,business_context:e.target.value})} placeholder="Business context" rows={4}/>
 <textarea value={form.objectives} onChange={e=>setForm({...form,objectives:e.target.value})} placeholder="Objectives (one per line)" rows={4}/>
 <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}><input value={form.voice} onChange={e=>setForm({...form,voice:e.target.value})} placeholder="Voice (e.g. marin)"/><input value={form.language} onChange={e=>setForm({...form,language:e.target.value})} placeholder="Language (e.g. en)"/></div>
 <input value={form.personality} onChange={e=>setForm({...form,personality:e.target.value})} placeholder="Personality"/>
 <textarea value={form.transfer_rules} onChange={e=>setForm({...form,transfer_rules:e.target.value})} placeholder={'Transfer rules JSON (optional), e.g. {"enabled":true,"conditions":["customer asks for human"]}'} rows={3}/>
 <textarea value={form.compliance} onChange={e=>setForm({...form,compliance:e.target.value})} placeholder={'Compliance JSON (optional), e.g. {"disclosure_required":true}'} rows={3}/>
 <div style={{display:'flex',gap:10}}><button disabled={saving}>{saving?'Creating…':'Create & Publish Agent'}</button><button type="button" onClick={()=>setShowCreate(false)}>Cancel</button></div>
 </form></div>}</section>:<section className="data card"><pre>{JSON.stringify(data,null,2)}</pre></section>}
 </main></div>}
