# ProductMaster-MCP

ProductMaster システム用 MCP (Model Context Protocol) サーバー

## 概要

ProductMaster システムの商品情報に対して、自然言語での曖昧検索を可能にするMCPサーバーです。
AIエージェントが商品情報を検索・分析できるようになります。

## 機能

### 🔍 柔軟な商品検索
- **商品タイプフィルター**: bond, stock, fund
- **通貨フィルター**: USD, JPY, EUR等
- **投資額範囲**: 最小・最大投資額での絞り込み
- **リスクレベル**: 1-5段階でのフィルタリング
- **発行者キーワード**: 部分一致検索
- **自然言語クエリ**: 商品名・説明・発行者での検索

### 📊 商品分析
- **商品詳細取得**: 商品コード指定での詳細情報
- **統計情報**: 商品分析・統計機能
- **グループ化**: タイプ・通貨・リスクレベル別の集計

### 🎯 曖昧検索の例

```python
# 例: "満期日がいつぐらいで、ドル建てで発行金額が大きい債券"
mcp.search_products_flexible(
    product_types=["bond"],
    currencies=["USD"],
    sort_by="investment_desc",
    limit=5
)

# 例: "高リスクな商品を教えて"
mcp.search_products_flexible(
    risk_levels=[4, 5],
    sort_by="risk_desc"
)

# 例: "トヨタ関連の商品"
mcp.search_products_flexible(
    query="トヨタ"
)
```

## 技術スタック

- **Python**: 3.8+
- **依存関係**: requests, typing-extensions
- **API**: ProductMaster REST API (localhost:8001)

## セットアップ

### 依存関係のインストール

```bash
cd server
pip install -r requirements.txt
```

### 基本テスト

```bash
cd tests
python debug_test.py
```

## API仕様

### 商品検索

```python
search_products_flexible(
    query="自然言語クエリ",
    product_types=["bond", "stock", "fund"],
    currencies=["USD", "JPY", "EUR"],
    investment_range={"min": 1000, "max": 100000},
    risk_levels=[1, 2, 3, 4, 5],
    issuer_keywords=["Apple", "Toyota"],
    sort_by="investment_desc",
    limit=10
)
```

### 商品詳細取得

```python
get_product_details("AAPL")
```

### 統計情報取得

```python
get_statistics()
```

## 将来の拡張

### Phase 2.2: AIChat MCP統合
- AIChat システムにMCP統合
- Claude 3.5 SonnetがProductMaster MCPを使用
- 自然言語での商品検索対話

### Phase 2.3: 高度な分析
- 商品推奨機能
- 対話的絞り込み
- 投資アドバイス機能

## バージョン

- **Version**: 1.0.0
- **Build Date**: 2025-08-26
- **Target**: ProductMaster System Integration
