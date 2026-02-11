#!/bin/bash

# Today X! Startup Script
# Usage: ./start.sh [demo|full]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔════════════════════════════════════════╗"
echo "║          Today X! Launcher             ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

MODE=${1:-demo}

case $MODE in
    demo)
        echo -e "${YELLOW}Starting in DEMO mode (mock data)...${NC}"
        echo ""
        echo "Running Python server on http://localhost:8000"
        echo "Press Ctrl+C to stop"
        echo ""
        ALL_PROXY= HTTP_PROXY= HTTPS_PROXY= python3 server.py
        ;;

    full)
        echo -e "${GREEN}Starting FULL mode with XRSS...${NC}"
        echo ""

        # Check for .env file
        if [ ! -f .env ]; then
            echo -e "${RED}Error: .env file not found!${NC}"
            echo ""
            echo "Please create .env file with your Twitter credentials:"
            echo "  cp .env.example .env"
            echo "  # Edit .env with your credentials"
            exit 1
        fi

        # Check for Docker
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}Error: Docker not installed!${NC}"
            echo "Please install Docker Desktop from https://docker.com"
            exit 1
        fi

        # Start Docker services
        echo "Starting Docker containers..."
        docker-compose up -d

        echo ""
        echo -e "${GREEN}Services started!${NC}"
        echo ""
        echo "  Frontend: http://localhost:8000"
        echo "  XRSS:     http://localhost:8001"
        echo ""
        echo "To view logs: docker-compose logs -f"
        echo "To stop:      docker-compose down"
        echo ""

        # Start Python server
        echo "Starting Python server..."
        ALL_PROXY= HTTP_PROXY= HTTPS_PROXY= XRSS_URL=http://localhost:8001 python3 server.py
        ;;

    stop)
        echo "Stopping Docker containers..."
        docker-compose down
        echo -e "${GREEN}Stopped.${NC}"
        ;;

    *)
        echo "Usage: ./start.sh [demo|full|stop]"
        echo ""
        echo "  demo  - Run with mock data (default)"
        echo "  full  - Run with XRSS (requires Docker + .env)"
        echo "  stop  - Stop Docker containers"
        ;;
esac
