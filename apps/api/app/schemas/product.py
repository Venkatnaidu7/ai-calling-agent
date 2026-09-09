from pydantic import BaseModel,Field
from datetime import datetime
class PhoneCreate(BaseModel): e164:str; agent_id:str|None=None; country:str|None=None; capabilities:dict={}
class ContactCreate(BaseModel): first_name:str|None=None; last_name:str|None=None; phone:str|None=None; email:str|None=None; tags:list[str]=[]; custom_fields:dict={}
class KnowledgeCreate(BaseModel): name:str; source_type:str='manual'; title:str; content:str=Field(min_length=1)
class AppointmentCreate(BaseModel): contact_id:str|None=None; start_at:datetime; end_at:datetime; timezone:str='Asia/Kolkata'; resource:str|None=None; location:str|None=None; meeting_url:str|None=None; notes:str|None=None
class CampaignCreate(BaseModel): name:str; concurrency:int=Field(default=1,ge=1,le=50); schedule:dict={}; retry_policy:dict={}
class HumanAgentCreate(BaseModel): name:str; phone:str; department:str|None=None; priority:int=0
class ToolCreate(BaseModel): name:str; description:str; schema:dict; enabled:bool=True
class ApiKeyCreate(BaseModel): name:str; scopes:list[str]=[]; expires_at:datetime|None=None
