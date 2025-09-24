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
from models import MCPRequest, MCPResponse
from tools_manager import ToolsManager
from tools.risk_filter import filter_products_by_risk_and_type

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=SERVER_CONFIG["title"], 
    version=SERVER_CONFIG["version"]
)

# ツール管理インスタンス
tools_manager = ToolsManager()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {
        "status": "healthy", 
        "service": "ProductMaster-MCP", 
        "timestamp": datetime.now().isoformat()
    }

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """MCPプロトコルエンドポイント"""
    print(f"[MCP_ENDPOINT] === REQUEST START ===")
    print(f"[MCP_ENDPOINT] Request received: {request}")
    
    try:
        method = request.method
        params = request.params
        
        if method == "initialize":
            # 初期化
            return MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "serverInfo": {
                        "name": SERVER_CONFIG["title"],
                        "version": SERVER_CONFIG["version"]
                    }
                }
            )
        
        elif method == "tools/list":
            # ツール一覧（一元管理から取得）
            return MCPResponse(
                id=request.id,
                result={
                    "tools": tools_manager.get_mcp_tools_format()
                }
            )
        
        elif method == "tools/call":
            # ツール実行
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            print(f"[MCP_ENDPOINT] Tool name: {tool_name}")
            print(f"[MCP_ENDPOINT] Arguments: {arguments}")
            
            # 動的ツール実行
            if tools_manager.is_valid_tool(tool_name):
                print(f"[MCP_ENDPOINT] Calling {tool_name}")
                tool_function = tools_manager.get_tool_function(tool_name)
                
                if tool_function:
                    tool_response = await tool_function(arguments)
                    tool_response.id = request.id
                    return tool_response
                else:
                    error_msg = f"Tool function not found: {tool_name}"
                    return MCPResponse(
                        id=request.id,
                        result=error_msg,
                        error=error_msg
                    )
            else:
                error_msg = f"Unknown tool: {tool_name}"
                return MCPResponse(
                    id=request.id,
                    result=error_msg,
                    error=error_msg
                )
        
        else:
            error_msg = f"Unknown method: {method}"
            return MCPResponse(
                id=request.id,
                result=error_msg,
                error=error_msg
            )
    
    except Exception as e:
        print(f"[MCP_ENDPOINT] EXCEPTION CAUGHT!")
        print(f"[MCP_ENDPOINT] Exception: {e}")
        
        return MCPResponse(
            id=request.id,
            result=f"サーバーエラー: {str(e)}",
            debug_response={
                "error": str(e),
                "error_type": type(e).__name__,
                "method": method,
                "params": params
            }
        )

@app.get("/tools")
async def list_available_tools():
    """MCPプロトコル準拠のツール一覧"""
    return {
        "tools": tools_manager.get_tools_list()
    }

@app.get("/tools/descriptions")
async def get_tool_descriptions():
    """ツール詳細情報（AIChat用）"""
    return {
        "tools": tools_manager.get_tools_descriptions()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVER_CONFIG["port"])
