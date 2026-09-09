import json,websockets
from app.core.config import get_settings
class RealtimeBridge:
    def __init__(self,instructions,voice='marin',language='en',tools=None):self.instructions=instructions;self.voice=voice;self.language=language;self.tools=tools or [];self.ws=None
    async def connect(self):
        s=get_settings()
        if not s.openai_api_key:raise RuntimeError('OPENAI_API_KEY is not configured')
        self.ws=await websockets.connect(f'{s.openai_realtime_url}?model={s.openai_realtime_model}',additional_headers={'Authorization':f'Bearer {s.openai_api_key}'},max_size=None,ping_interval=20,ping_timeout=20)
        session={'type':'realtime','instructions':self.instructions,'voice':self.voice,'output_modalities':['audio'],'audio':{'input':{'format':{'type':'audio/pcmu'},'turn_detection':{'type':'server_vad','interrupt_response':True,'create_response':True,'silence_duration_ms':450}},'output':{'format':{'type':'audio/pcmu'}}},'max_output_tokens':512}
        if self.tools:session['tools']=self.tools;session['tool_choice']='auto'
        await self.ws.send(json.dumps({'type':'session.update','session':session}))
    async def send_audio(self,payload):await self.ws.send(json.dumps({'type':'input_audio_buffer.append','audio':payload}))
    async def events(self):
        async for raw in self.ws:yield json.loads(raw)
    async def cancel(self):
        if self.ws:await self.ws.send(json.dumps({'type':'response.cancel'}))
    async def tool_result(self,call_id,result):
        await self.ws.send(json.dumps({'type':'conversation.item.create','item':{'type':'function_call_output','call_id':call_id,'output':json.dumps(result)}}));await self.ws.send(json.dumps({'type':'response.create','response':{'output_modalities':['audio']}}))
    async def close(self):
        if self.ws:await self.ws.close()
