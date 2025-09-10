# ProductMaster MCP 設計書

## 📋 システム概要

### システム名
**ProductMaster MCP Server** - 商品検索Model Context Protocol サーバー

### 目的
- Model Context Protocol (MCP) 準拠の商品検索API提供
- AIChat System との連携による商品情報検索
- 高速・軽量な商品データアクセス
- 拡張可能なMCPアーキテクチャの実装例

## 🏗️ アーキテクチャ

### 技術スタック
- **Backend**: Python 3.9+, FastAPI
- **Protocol**: Model Context Protocol (MCP) v1.0
- **Database**: PostgreSQL (productmaster DB) 接続
- **Communication**: HTTP REST API
- **Deployment**: systemd, Nginx reverse proxy

### システム構成
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AIChat        │    │   Nginx Proxy   │    │  MCP Server     │
│   System        │◄──►│(/mcp/products/) │◄──►│   (Port 8003)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │ PostgreSQL DB   │
                                               │(productmaster)  │
                                               └─────────────────┘
```

## 🔧 MCP プロトコル実装

### MCP 仕様準拠
```python
class MCPServer:
    """Model Context Protocol Server Implementation"""
    
    def __init__(self):
        self.name = "ProductMaster"
        self.version = "1.0.0"
        self.description = "金融商品情報検索・管理MCP サーバー"
        self.capabilities = [
            "search",      # 商品検索
            "get",         # 商品詳細取得
            "list",        # 商品一覧取得
            "filter",      # 条件絞り込み
            "health"       # ヘルスチェック
        ]
```

### MCP メソッド実装
```python
# 商品検索
async def mcp_search(params: dict) -> dict:
    """
    商品検索MCP メソッド
    
    Parameters:
    - query: 検索クエリ（商品名・コード）
    - type: 商品種別フィルタ（bond/stock/fund）
    - risk_level: リスクレベルフィルタ（1-5）
    - limit: 取得件数制限（デフォルト: 10）
    """
    
# 商品詳細取得
async def mcp_get(params: dict) -> dict:
    """
    商品詳細取得MCP メソッド
    
    Parameters:
    - product_code: 商品コード
    - include_related: 関連商品含む（デフォルト: false）
    """
    
# 商品一覧取得
async def mcp_list(params: dict) -> dict:
    """
    商品一覧取得MCP メソッド
    
    Parameters:
    - offset: オフセット（デフォルト: 0）
    - limit: 取得件数（デフォルト: 20）
    - sort: ソート順（name/code/risk_level）
    """
```

## 🎯 API仕様

### エンドポイント一覧
```
# MCP Core
POST /mcp/search           # 商品検索
POST /mcp/get              # 商品詳細取得
POST /mcp/list             # 商品一覧取得
POST /mcp/filter           # 条件絞り込み

# MCP Management
GET  /mcp/capabilities     # サーバー機能一覧
GET  /mcp/info             # サーバー情報
GET  /health               # ヘルスチェック

# Legacy Support (非MCP)
GET  /api/products         # 商品一覧（互換性）
GET  /api/search           # 商品検索（互換性）
```

### MCP リクエスト/レスポンス形式

#### 検索リクエスト例
```json
{
  "method": "search",
  "params": {
    "query": "トヨタ",
    "type": "bond",
    "risk_level": [1, 2],
    "limit": 5
  },
  "id": "req_001",
  "timestamp": "2025-09-05T10:00:00Z"
}
```

#### 検索レスポンス例
```json
{
  "id": "req_001",
  "result": {
    "products": [
      {
        "product_code": "JP-TOYOTA-2027",
        "product_name": "トヨタ自動車第51回社債",
        "product_type": "bond",
        "currency": "JPY",
        "issuer": "トヨタ自動車株式会社",
        "risk_level": 2,
        "minimum_investment": 1000000.00,
        "description": "世界最大の自動車メーカーが発行する安定性の高い社債。"
      }
    ],
    "total": 1,
    "execution_time": 0.15,
    "server_info": {
      "name": "ProductMaster",
      "version": "1.0.0",
      "capabilities": ["search", "get", "list", "filter"]
    }
  },
  "timestamp": "2025-09-05T10:00:00.150Z"
}
```

## 🔧 実装詳細

### データベース接続
```python
import asyncpg
from typing import List, Dict, Optional

class ProductDatabase:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(self.connection_string)
    
    async def search_products(
        self, 
        query: str, 
        product_type: Optional[str] = None,
        risk_level: Optional[List[int]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """商品検索クエリ実行"""
        
        sql = """
        SELECT product_code, product_name, product_type, currency, 
               issuer, risk_level, minimum_investment, description
        FROM products 
        WHERE is_active = true
        """
        
        params = []
        param_count = 0
        
        if query:
            param_count += 1
            sql += f" AND (product_name ILIKE ${param_count} OR product_code ILIKE ${param_count})"
            params.append(f"%{query}%")
        
        if product_type:
            param_count += 1
            sql += f" AND product_type = ${param_count}"
            params.append(product_type)
        
        if risk_level:
            param_count += 1
            sql += f" AND risk_level = ANY(${param_count})"
            params.append(risk_level)
        
        sql += f" ORDER BY product_name LIMIT {limit}"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]
```

### エラーハンドリング
```python
class MCPError(Exception):
    """MCP 固有エラー"""
    def __init__(self, code: int, message: str, data: dict = None):
        self.code = code
        self.message = message
        self.data = data or {}

class MCPErrorCodes:
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000

async def handle_mcp_error(error: Exception) -> dict:
    """MCP エラーレスポンス生成"""
    if isinstance(error, MCPError):
        return {
            "error": {
                "code": error.code,
                "message": error.message,
                "data": error.data
            }
        }
    else:
        return {
            "error": {
                "code": MCPErrorCodes.INTERNAL_ERROR,
                "message": "Internal server error",
                "data": {"detail": str(error)}
            }
        }
```

## 🚀 デプロイメント

### systemd設定
```ini
[Unit]
Description=ProductMaster MCP Server
After=network.target postgresql.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/ProductMaster-MCP
ExecStart=/usr/bin/python3 simple_http_mcp_8003.py
Restart=always
RestartSec=3
Environment=PYTHONPATH=/home/ec2-user/ProductMaster-MCP

[Install]
WantedBy=multi-user.target
```

### 設定ファイル
```python
# config.py
import os

# データベース設定
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/productmaster"
)

# MCP サーバー設定
MCP_SERVER_CONFIG = {
    "name": "ProductMaster",
    "version": "1.0.0",
    "description": "金融商品情報検索・管理MCP サーバー",
    "host": "0.0.0.0",
    "port": 8003,
    "max_connections": 100,
    "timeout": 30
}

# ログ設定
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "/var/log/productmaster-mcp.log"
```

## 📊 パフォーマンス

### 目標値
- **検索レスポンス**: < 100ms
- **詳細取得**: < 50ms
- **同時接続**: 50接続
- **スループット**: 1000 req/sec

### 最適化施策
```python
# 接続プール最適化
async def optimize_database_pool():
    return await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=20,
        max_queries=50000,
        max_inactive_connection_lifetime=300
    )

# クエリ最適化
async def optimized_search(query: str):
    # インデックス活用
    sql = """
    SELECT * FROM products 
    WHERE search_vector @@ plainto_tsquery('japanese', $1)
    AND is_active = true
    ORDER BY ts_rank(search_vector, plainto_tsquery('japanese', $1)) DESC
    LIMIT 10
    """
```

## 🔒 セキュリティ

### 入力検証
```python
from pydantic import BaseModel, validator
from typing import Optional, List

class SearchRequest(BaseModel):
    query: str
    type: Optional[str] = None
    risk_level: Optional[List[int]] = None
    limit: int = 10
    
    @validator('query')
    def validate_query(cls, v):
        if len(v) > 100:
            raise ValueError('クエリが長すぎます')
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 100:
            raise ValueError('取得件数の上限は100件です')
        return v
```

### レート制限
```python
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        client_requests = self.requests[client_id]
        
        # 古いリクエストを削除
        client_requests[:] = [req_time for req_time in client_requests 
                             if now - req_time < self.window]
        
        if len(client_requests) >= self.max_requests:
            return False
        
        client_requests.append(now)
        return True
```

## 🧪 テスト戦略

### テストケース
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_mcp_search():
    """MCP 検索機能テスト"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/mcp/search", json={
            "method": "search",
            "params": {"query": "トヨタ", "limit": 5}
        })
    
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "products" in data["result"]
    assert len(data["result"]["products"]) <= 5

@pytest.mark.asyncio
async def test_mcp_get():
    """MCP 詳細取得テスト"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/mcp/get", json={
            "method": "get",
            "params": {"product_code": "JP-TOYOTA-2027"}
        })
    
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["product_code"] == "JP-TOYOTA-2027"

@pytest.mark.asyncio
async def test_health_check():
    """ヘルスチェックテスト"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

## 📈 監視・運用

### ログ設定
```python
import logging
import json

class MCPLogger:
    def __init__(self):
        self.logger = logging.getLogger("productmaster-mcp")
        
    def log_mcp_request(self, method: str, params: dict, execution_time: float):
        self.logger.info(json.dumps({
            "type": "mcp_request",
            "method": method,
            "params": params,
            "execution_time": execution_time,
            "timestamp": time.time()
        }))
```

### メトリクス収集
```python
class MCPMetrics:
    def __init__(self):
        self.request_count = defaultdict(int)
        self.response_times = defaultdict(list)
        self.error_count = defaultdict(int)
    
    def record_request(self, method: str, response_time: float, success: bool):
        self.request_count[method] += 1
        self.response_times[method].append(response_time)
        if not success:
            self.error_count[method] += 1
```

## 🔄 今後の拡張計画

### 短期（1-3ヶ月）
- **キャッシュ機能**: Redis による検索結果キャッシュ
- **バッチ処理**: 複数商品の一括取得
- **フィルタ拡張**: より詳細な検索条件

### 中期（3-6ヶ月）
- **WebSocket対応**: リアルタイム通信
- **GraphQL**: より柔軟なクエリ
- **認証機能**: JWT トークン認証

### 長期（6ヶ月以降）
- **分散処理**: 複数インスタンス対応
- **機械学習**: 検索結果の最適化
- **外部API**: 他社データ連携

---

**Document Version**: v1.0.0  
**Repository**: https://github.com/takehig/ProductMaster-MCP  
**Last Updated**: 2025-09-05
