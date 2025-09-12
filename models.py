# ProductMaster MCP Data Models

from pydantic import BaseModel
from typing import Dict, Any, Optional

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Any = None
    error: Optional[str] = None
    debug_response: Optional[Dict[str, Any]] = None

class ToolDescription(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]
