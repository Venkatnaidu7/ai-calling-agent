from pydantic import BaseModel
class ErrorBody(BaseModel): code:str; message:str; request_id:str
class ErrorResponse(BaseModel): error:ErrorBody
class Page(BaseModel): items:list; next_cursor:str|None=None
class Message(BaseModel): message:str
