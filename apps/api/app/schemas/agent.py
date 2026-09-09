from pydantic import BaseModel,Field,ConfigDict
class AgentCreate(BaseModel): name:str=Field(min_length=1,max_length=200); description:str|None=None
class AgentOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:str; tenant_id:str; name:str; description:str|None; active_version_id:str|None; active:bool
class AgentVersionCreate(BaseModel):
    greeting:str='Hello! How can I help you today?'; system_instructions:str; voice:str='marin'; language:str='en'; personality:str='professional, warm'; business_context:str|None=None; objectives:list[str]=[]; transfer_rules:dict={}; compliance:dict={}
class AgentVersionOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:str; agent_id:str; version:int; status:str; greeting:str; system_instructions:str; voice:str; language:str
