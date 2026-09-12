import json
import websockets
from app.core.config import get_settings

HANDOFF_TOOL = {
    'type': 'function',
    'name': 'transfer_to_human',
    'description': 'Transfer the active caller to a human support agent when the caller requests a person or configured escalation rules require human assistance. Do not use for ordinary questions the AI can safely answer.',
    'parameters': {
        'type': 'object',
        'properties': {
            'reason': {'type': 'string', 'description': 'Short reason for escalation.'},
            'routing_group_id': {'type': 'string', 'description': 'Optional routing group UUID.'},
            'destination_id': {'type': 'string', 'description': 'Optional transfer destination UUID.'},
        },
        'required': ['reason'],
        'additionalProperties': False,
    },
}

class RealtimeBridge:
    """Server-side OpenAI Realtime bridge for Twilio/Plivo G.711 μ-law audio."""
    def __init__(self, instructions, voice='marin', language='en', tools=None):
        self.instructions=instructions or 'You are a helpful phone assistant.'; self.voice=voice or 'marin'; self.language=language or 'en'; self.tools=tools or []; self.ws=None
    async def connect(self):
        settings=get_settings()
        if not settings.openai_api_key: raise RuntimeError('OPENAI_API_KEY is not configured')
        self.ws=await websockets.connect(f'{settings.openai_realtime_url}?model={settings.openai_realtime_model}',additional_headers={'Authorization':f'Bearer {settings.openai_api_key}'},max_size=None,ping_interval=20,ping_timeout=20)
        session={'type':'realtime','instructions':self.instructions,'voice':self.voice,'output_modalities':['audio'],'audio':{'input':{'format':{'type':'audio/pcmu'},'transcription':{'model':'gpt-4o-mini-transcribe','language':self.language},'turn_detection':{'type':'server_vad','interrupt_response':True,'create_response':True,'silence_duration_ms':450}},'output':{'format':{'type':'audio/pcmu'}}}}
        if self.tools: session['tools']=self.tools; session['tool_choice']='auto'
        await self.ws.send(json.dumps({'type':'session.update','session':session}))
    async def send_audio(self,payload):
        if self.ws: await self.ws.send(json.dumps({'type':'input_audio_buffer.append','audio':payload}))
    async def events(self):
        if not self.ws: return
        async for raw in self.ws: yield json.loads(raw)
    async def cancel(self):
        if self.ws: await self.ws.send(json.dumps({'type':'response.cancel'}))
    async def create_response(self):
        if self.ws: await self.ws.send(json.dumps({'type':'response.create','response':{'output_modalities':['audio']}}))
    async def tool_result(self,call_id,result):
        if not self.ws: return
        await self.ws.send(json.dumps({'type':'conversation.item.create','item':{'type':'function_call_output','call_id':call_id,'output':json.dumps(result)}})); await self.create_response()
    async def close(self):
        if self.ws: await self.ws.close(); self.ws=None
