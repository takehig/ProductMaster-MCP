# ProductMaster MCP Configuration

# データベース設定
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'productmaster',
    'user': 'productmaster_user',
    'password': 'productmaster123'
}

# Bedrock設定
BEDROCK_CONFIG = {
    "region_name": "us-east-1",
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
}

# サーバー設定
SERVER_CONFIG = {
    "title": "ProductMaster MCP Server",
    "version": "2.0.0",
    "port": 8003
}
