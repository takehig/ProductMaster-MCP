# ProductMaster MCP Data Models

from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    result: Any
    error: Optional[Dict[str, Any]] = None

class ToolDescription(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]
