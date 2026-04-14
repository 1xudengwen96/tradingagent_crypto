#!/bin/bash
# 交易机器人启动脚本
# 用法: ./start.sh [--port 8000] [--host 0.0.0.0]

set -e

cd "$(dirname "$0")"

# 默认配置
PORT=8000
HOST="0.0.0.0"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            echo "用法: $0 [--port PORT] [--host HOST]"
            exit 1
            ;;
    esac
done

# 检查 Python 虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 未找到 .venv 虚拟环境，请先运行: uv sync 或 python3 -m venv .venv"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖
if ! python3 -c "import fastapi, uvicorn, langgraph" 2>/dev/null; then
    echo "❌ 依赖未安装，正在安装..."
    uv sync || pip install -r requirements.txt
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，请从 .env.example 复制并配置"
    echo "   运行: cp .env.example .env"
    exit 1
fi

# 加载 .env 环境变量
set -a
source .env
set +a

echo ""
echo "=========================================="
echo "  加密货币交易机器人"
echo "=========================================="
echo "  监听地址: $HOST:$PORT"
echo "  虚拟环境: .venv"
echo "  配置文件: .env"
echo "=========================================="
echo ""

# 启动服务
exec python3 server.py --host "$HOST" --port "$PORT"
