#!/bin/bash

# Database Connection Health Check Script
# This script provides quick database connection monitoring

echo "=== The Wall Database Connection Health Check ==="
echo "Timestamp: $(date)"
echo ""

# Check if Django is available
if ! command -v python &> /dev/null; then
    echo "❌ Python not found"
    exit 1
fi

# Check if manage.py exists
if [ ! -f "thewall/manage.py" ]; then
    echo "❌ Django manage.py not found. Run from project root."
    exit 1
fi

cd thewall

echo "🔍 Checking database connection status..."
python manage.py db_connections --action=status

echo ""
echo "🏥 Running health check..."
python manage.py db_connections --action=health

echo ""
echo "📊 Connection pool configuration:"
echo "Current environment variables:"
echo "  DB_MAX_CONNS: ${DB_MAX_CONNS:-'Not set (using defaults)'}"
echo "  DB_HOST: ${DB_HOST:-'Not set'}"
echo "  DB_NAME: ${DB_NAME:-'Not set'}"

# Check if PostgreSQL is accessible
echo ""
echo "🐘 Testing PostgreSQL connectivity..."
if python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'wall'),
        user=os.getenv('DB_USER', 'wall'),
        password=os.getenv('DB_PASSWORD', 'wall'),
        port=os.getenv('DB_PORT', '5432')
    )
    print('✅ PostgreSQL connection successful')
    conn.close()
except Exception as e:
    print(f'❌ PostgreSQL connection failed: {e}')
    exit(1)
" 2>/dev/null; then
    echo ""
else
    echo "⚠️  PostgreSQL connectivity test requires psycopg2"
fi

echo ""
echo "💡 Quick fixes for connection issues:"
echo "   • Close idle connections: python manage.py db_connections --action=close-idle"
echo "   • Monitor continuously: python manage.py db_connections --action=monitor --watch"
echo "   • Reduce pool size: export DB_MAX_CONNS=15"
echo ""
echo "📖 Full documentation: docs/database-connections.md"
