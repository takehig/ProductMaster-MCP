import json
import importlib
from typing import Dict, List, Any, Optional

class ToolsManager:
    """ツール定義の一元管理クラス"""
    
    def __init__(self, config_path: str = "tools_config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """tools/list用のツール一覧"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": tool["parameters"],
                    "required": ["text_input"]
                }
            }
            for tool in self.config["tools"]
        ]
    
    def get_tools_descriptions(self) -> List[Dict[str, Any]]:
        """/tools/descriptions用の詳細情報"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "usage_context": tool["usage_context"],
                "parameters": tool["parameters"]
            }
            for tool in self.config["tools"]
        ]
    
    def get_mcp_tools_format(self) -> List[Dict[str, Any]]:
        """MCPプロトコル用のツール一覧"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "usage_context": tool["usage_context"],
                "parameters": tool["parameters"]
            }
            for tool in self.config["tools"]
        ]
    
    def get_tool_function(self, tool_name: str):
        """ツール名から関数を動的取得"""
        for tool in self.config["tools"]:
            if tool["name"] == tool_name:
                try:
                    module = importlib.import_module(tool["module_path"])
                    return getattr(module, tool["function_name"])
                except (ImportError, AttributeError) as e:
                    print(f"[ToolsManager] Failed to import {tool_name}: {e}")
                    return None
        return None
    
    def is_valid_tool(self, tool_name: str) -> bool:
        """ツール名の有効性チェック"""
        return any(tool["name"] == tool_name for tool in self.config["tools"])
    
    def get_tool_names(self) -> List[str]:
        """全ツール名のリスト"""
        return [tool["name"] for tool in self.config["tools"]]
