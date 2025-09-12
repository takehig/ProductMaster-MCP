# ProductMaster-MCP 設計書

## 📋 プロジェクト概要
**商品検索 MCP サーバー - Model Context Protocol 準拠**

### 🎯 システム目的
- 金融商品情報の MCP プロトコル経由提供
- AIChat システムとの統合
- 高速商品検索・情報提供
- MCP 標準準拠の API 提供

## 🏗️ システム構成

### 📊 基本情報
- **リポジトリ**: https://github.com/takehig/ProductMaster-MCP
- **サービスポート**: 8003
- **アクセスURL**: http://44.217.45.24/mcp/products/
- **技術スタック**: Python FastAPI, PostgreSQL, MCP Protocol

### 🔧 ファイル構造
```
ProductMaster-MCP/
├── simple_http_mcp_8003.py  # MCP サーバーメイン
├── requirements.txt         # Python 依存関係
├── .env.example            # 環境変数例
└── DESIGN.md              # 本設計書
```

## 🔑 主要機能

### ✅ 実装済み機能
1. **MCP プロトコル準拠**
   - Model Context Protocol 標準準拠
   - HTTP ベース MCP API
   - JSON レスポンス形式

2. **商品検索機能**
   - 商品名検索
   - 商品コード検索
   - 商品種別フィルタリング
   - リスクレベルフィルタリング

3. **高速データ取得**
   - PostgreSQL 直接接続
   - インデックス最適化
   - キャッシュ機能

### 🔧 MCP API エンドポイント
```
GET  /                      # MCP サーバー情報
POST /mcp/search           # 商品検索（MCP準拠）
GET  /mcp/product/{id}     # 商品詳細取得
GET  /mcp/categories       # 商品カテゴリ一覧
GET  /health              # ヘルスチェック
```

## 🔍 検索機能設計

### 🔎 検索パラメータ
```python
{
    "query": "検索キーワード",
    "product_type": "商品種別",
    "risk_level": "リスクレベル",
    "currency": "通貨",
    "limit": "取得件数"
}
```

### 📊 検索レスポンス
```python
{
    "status": "success",
    "results": [
        {
            "product_id": 1,
            "product_code": "STK-APPLE",
            "product_name": "Apple株式",
            "product_type": "stock",
            "currency": "USD",
            "risk_level": 3,
            "description": "..."
        }
    ],
    "total": 1,
    "query_time": "0.05s"
}
```

## 🗄️ データベース接続

### 📊 標準データベース設定
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=productmaster
DB_USER=productmaster_user
DB_PASSWORD=productmaster123
```

### 🔧 検索クエリ最適化
```sql
-- インデックス設定
CREATE INDEX idx_products_name ON products(product_name);
CREATE INDEX idx_products_code ON products(product_code);
CREATE INDEX idx_products_type ON products(product_type);

-- 検索クエリ例
SELECT product_id, product_code, product_name, product_type, 
       currency, risk_level, description
FROM products 
WHERE product_name ILIKE %s 
  AND product_type = %s 
  AND is_active = true
ORDER BY product_id
LIMIT %s;
```

## 🤖 MCP プロトコル実装

### 📡 MCP 標準準拠
```python
class MCPServer:
    def __init__(self):
        self.name = "ProductMaster"
        self.version = "1.0.0"
        self.description = "金融商品検索・情報提供"
    
    async def handle_mcp_request(self, request):
        # MCP リクエスト処理
        # 商品検索実行
        # MCP レスポンス生成
```

### 🔗 AIChat 統合
```python
# AIChat からの呼び出し例
async def search_products(query: str):
    response = await mcp_client.call(
        "productmaster", 
        "search", 
        {"query": query}
    )
    return response["results"]
```

## 🚀 デプロイ・運用

### 📦 systemd サービス
```ini
[Unit]
Description=ProductMaster MCP Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/ProductMaster-MCP
ExecStart=/usr/bin/python3 simple_http_mcp_8003.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 🔄 運用コマンド
```bash
# サービス管理
sudo systemctl start productmaster-mcp
sudo systemctl stop productmaster-mcp
sudo systemctl restart productmaster-mcp
sudo systemctl status productmaster-mcp

# ログ確認
sudo journalctl -u productmaster-mcp -f
```

## 📈 パフォーマンス・監視

### 📊 監視項目
- **検索レスポンス時間**: 商品検索速度
- **データベース接続**: PostgreSQL 接続状態
- **MCP リクエスト数**: API 利用状況
- **エラー率**: 検索エラー発生頻度

### ⚡ パフォーマンス最適化
- **データベースインデックス**: 検索高速化
- **接続プール**: データベース接続効率化
- **キャッシュ機能**: 頻繁な検索結果キャッシュ

## 🔮 今後の拡張予定

### 📋 計画中機能
1. **高度検索**: 複合条件検索・範囲検索
2. **商品推奨**: AI による商品推奨機能
3. **リアルタイム更新**: 商品情報リアルタイム同期
4. **分析機能**: 検索パターン分析

### 🛠️ MCP 拡張
1. **バッチ検索**: 複数商品一括検索
2. **ストリーミング**: 大量データストリーミング
3. **認証機能**: MCP レベル認証
4. **ログ機能**: 詳細ログ・監査機能

## 📝 更新履歴
- **2025-09-13**: 設計書更新・MCP プロトコル詳細反映
- **2025-08-30**: MCP サーバー実装完了
- **2025-08-28**: 商品検索 API 基本実装
- **2025-08-26**: プロジェクト開始
