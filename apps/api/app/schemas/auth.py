from pydantic import BaseModel,EmailStr,Field
class RegisterIn(BaseModel):
    business_name:str=Field(min_length=2,max_length=200); email:EmailStr; password:str=Field(min_length=10,max_length=128)
class LoginIn(BaseModel): email:EmailStr; password:str
class TokenOut(BaseModel): access_token:str; token_type:str='bearer'
