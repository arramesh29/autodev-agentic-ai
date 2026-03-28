from pydantic import BaseModel
from typing import Optional, Dict, Any


class AgentRequest(BaseModel):
    query: str


class AgentResponse(BaseModel):
    status: str
    action: Optional[str]
    data: Optional[Dict[str, Any]]
    error: Optional[str]
