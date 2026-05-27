#!/bin/bash
# Sovereign Temple Startup Script
# Usage: ./start-sovereign.sh [local|docker]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║              🏛️  SOVEREIGN TEMPLE MCP  🏛️               ║"
    echo "║                                                           ║"
    echo "║     Neural • Memory • Monitoring • Multi-Agent • Care    ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_dependencies() {
    print_info "Checking dependencies..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found. Docker mode will not be available."
    fi
    
    if ! command -v psql &> /dev/null; then
        print_warning "PostgreSQL client (psql) not found."
    fi
    
    print_status "Dependencies checked"
}

setup_local() {
    print_info "Setting up local environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_info "Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    
    # Create necessary directories
    mkdir -p models logs
    
    print_status "Local environment ready"
}

start_local() {
    print_info "Starting Sovereign Temple (Local Mode)..."
    
    setup_local
    
    # Check if PostgreSQL is running locally
    if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        print_status "PostgreSQL is running"
    else
        print_warning "PostgreSQL not detected on localhost:5432"
        print_info "Starting with SQLite fallback (limited functionality)..."
    fi
    
    # Start the server
    print_info "Starting MCP server on port 3100..."
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  Server starting... Press Ctrl+C to stop                 ║"
    echo "║  Endpoint: http://localhost:3100                         ║"
    echo "║  Health:   http://localhost:3100/health                  ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    python sovereign-mcp-server.py
}

start_docker() {
    print_info "Starting Sovereign Temple (Docker Mode)..."
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        echo "OPENAI_API_KEY=your_openai_key_here" > .env
        print_info "Please edit .env and add your OpenAI API key"
    fi
    
    # Start services
    print_info "Starting Docker services..."
    docker-compose up --build -d
    
    print_status "Docker services starting..."
    print_info "Waiting for services to be healthy..."
    
    # Wait for services
    sleep 5
    
    # Check health
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://localhost:3100/health > /dev/null 2>&1; then
            print_status "Sovereign Temple is healthy and ready!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -n "."
        sleep 2
    done
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        print_error "Services failed to start. Check logs with: docker-compose logs"
        exit 1
    fi
    
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              🎉 Sovereign Temple is LIVE! 🎉             ║"
    echo "║                                                           ║"
    echo "║  MCP Endpoint: http://localhost:3100/mcp                 ║"
    echo "║  Health Check: http://localhost:3100/health              ║"
    echo "║  PostgreSQL:   localhost:5432                            ║"
    echo "║  Weaviate:     localhost:8080                            ║"
    echo "║                                                           ║"
    echo "║  View logs:    docker-compose logs -f                    ║"
    echo "║  Stop:         docker-compose down                       ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

stop_docker() {
    print_info "Stopping Sovereign Temple..."
    docker-compose down
    print_status "Services stopped"
}

train_models() {
    print_info "Training neural models..."
    
    setup_local
    source venv/bin/activate
    
    python3 << 'PYTHON'
import sys
sys.path.insert(0, 'neural-core')
from neural_core import create_default_registry

registry = create_default_registry("models")
print("Training all models...")
results = registry.train_all()

for name, metrics in results.items():
    print(f"\n{name}:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value}")

print("\n✓ All models trained and saved")
PYTHON
}

show_help() {
    echo "Usage: ./start-sovereign.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  local       Start in local mode (requires Python 3.11+)"
    echo "  docker      Start with Docker Compose (recommended)"
    echo "  stop        Stop Docker services"
    echo "  train       Train all neural models"
    echo "  status      Check system status"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./start-sovereign.sh docker    # Start with Docker"
    echo "  ./start-sovereign.sh local     # Start locally"
}

check_status() {
    print_info "Checking Sovereign Temple status..."
    
    # Check if server is running
    if curl -s http://localhost:3100/health > /dev/null 2>&1; then
        print_status "MCP Server is running"
        curl -s http://localhost:3100/health | python3 -m json.tool 2>/dev/null || true
    else
        print_error "MCP Server is not running"
    fi
    
    # Check Docker services
    if docker ps | grep -q sovereign; then
        print_status "Docker services are running"
        docker ps --filter "name=sovereign" --format "table {{.Names}}\t{{.Status}}"
    fi
}

# Main
print_banner

case "${1:-help}" in
    local)
        check_dependencies
        start_local
        ;;
    docker)
        check_dependencies
        start_docker
        ;;
    stop)
        stop_docker
        ;;
    train)
        train_models
        ;;
    status)
        check_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
