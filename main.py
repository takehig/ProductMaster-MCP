#!/usr/bin/env python3
"""
ProductMaster MCP Server - 商品検索API
Port: 8003
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import SERVER_CONFIG
from models import MCPRequest, MCPResponse, ToolDescription
from tools.product_search import get_product_details

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=SERVER_CONFIG["title"], 
    version=SERVER_CONFIG["version"]
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_tool_descriptions():
    """利用可能なツールの説明を取得"""
    return [
        ToolDescription(
            name="get_product_details",
            description="商品詳細情報を検索・取得します。商品コード、商品名、満期日などで検索可能です。",
            inputSchema={
                "type": "object",
                "properties": {
                    "text_input": {
                        "type": "string",
                        "description": "検索条件（商品コード、商品名、満期日など）"
                    }
                },
                "required": ["text_input"]
            }
        )
    ]

@app.get("/")
async def root():
    return {
        "service": "ProductMaster MCP Server",
        "version": SERVER_CONFIG["version"],
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ProductMaster-MCP", "timestamp": datetime.now().isoformat()}

@app.get("/tools")
async def list_available_tools():
    """利用可能なツール一覧"""
    tools = await get_tool_descriptions()
    return {"tools": [tool.dict() for tool in tools]}

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """MCP プロトコルエンドポイント"""
    try:
        if request.method == "tools/list":
            tools = await get_tool_descriptions()
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {"tools": [tool.dict() for tool in tools]}
            }
        
        elif request.method == "tools/call":
            tool_name = request.params.get("name") if request.params else None
            tool_arguments = request.params.get("arguments", {}) if request.params else {}
            
            if tool_name == "get_product_details":
                result = await get_product_details(tool_arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "result": {
                        "content": [{"type": "text", "text": result.result}],
                        "_meta": result.debug_response
                    }
                }
            else:
                raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {request.method}")
    
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {"code": -32603, "message": str(e)}
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVER_CONFIG["port"])
