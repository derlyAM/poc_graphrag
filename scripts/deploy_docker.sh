#!/bin/bash

# ==============================================================================
# Docker Deployment Script - RAG System
# ==============================================================================
# Quick deployment script for Docker Compose setup
#
# Usage:
#   ./scripts/deploy_docker.sh [command]
#
# Commands:
#   build       - Build Docker images
#   start       - Start all services
#   stop        - Stop all services
#   restart     - Restart all services
#   logs        - Show logs
#   status      - Show service status
#   clean       - Stop and remove containers
#   rebuild     - Rebuild and restart everything
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if .env exists
check_env() {
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        echo "Creating .env from .env.docker template..."
        cp .env.docker .env
        print_warning "Please update .env with your OPENAI_API_KEY"
        exit 1
    fi

    # Check if OPENAI_API_KEY is set
    if grep -q "your_openai_api_key_here" .env; then
        print_warning ".env file contains placeholder API key"
        print_warning "Please update OPENAI_API_KEY in .env file"
        exit 1
    fi

    print_success ".env file configured"
}

# Check Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running!"
        echo "Please start Docker Desktop and try again"
        exit 1
    fi
    print_success "Docker is running"
}

# Build images
build_images() {
    print_header "Building Docker Images"
    check_env
    check_docker

    echo "Building all services..."
    docker-compose build

    print_success "Images built successfully"
}

# Start services
start_services() {
    print_header "Starting Services"
    check_env
    check_docker

    # Create directories if they don't exist
    mkdir -p storage/qdrant_storage logs data

    echo "Starting all services in detached mode..."
    docker-compose up -d

    echo ""
    print_success "Services started!"
    echo ""
    echo "Waiting for services to become healthy (this may take 40-60 seconds)..."
    sleep 10

    # Wait for services to be healthy
    max_wait=60
    elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        if docker-compose ps | grep -q "healthy"; then
            echo ""
            print_success "Services are healthy!"
            break
        fi
        echo -n "."
        sleep 5
        elapsed=$((elapsed + 5))
    done

    echo ""
    echo ""
    print_header "Service URLs"
    echo "  Qdrant Dashboard:  http://localhost:6333/dashboard"
    echo "  API Docs (Swagger): http://localhost:8000/docs"
    echo "  API Health Check:   http://localhost:8000/health"
    echo "  Streamlit UI:       http://localhost:8501"
    echo ""
    echo "View logs with: $0 logs"
}

# Stop services
stop_services() {
    print_header "Stopping Services"
    docker-compose stop
    print_success "Services stopped"
}

# Restart services
restart_services() {
    print_header "Restarting Services"
    docker-compose restart
    print_success "Services restarted"
}

# Show logs
show_logs() {
    print_header "Service Logs (Ctrl+C to exit)"
    docker-compose logs -f --tail=100
}

# Show status
show_status() {
    print_header "Service Status"
    docker-compose ps
    echo ""

    # Health checks
    echo "Health Checks:"
    echo ""

    # Check API
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        print_success "API is healthy"
    else
        print_error "API is not responding"
    fi

    # Check Qdrant
    if curl -sf http://localhost:6333/health > /dev/null 2>&1; then
        print_success "Qdrant is healthy"
    else
        print_error "Qdrant is not responding"
    fi

    # Check Streamlit
    if curl -sf http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        print_success "Streamlit is healthy"
    else
        print_error "Streamlit is not responding"
    fi
}

# Clean services
clean_services() {
    print_header "Cleaning Services"
    print_warning "This will stop and remove all containers"
    echo "Volumes (data) will be preserved"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down
        print_success "Services cleaned"
    else
        echo "Cancelled"
    fi
}

# Rebuild everything
rebuild_all() {
    print_header "Rebuilding Everything"
    print_warning "This will rebuild images and restart services"
    echo ""

    stop_services
    echo ""

    print_header "Building Images (no cache)"
    docker-compose build --no-cache
    echo ""

    start_services
}

# Main command handler
case "${1:-}" in
    build)
        build_images
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    clean)
        clean_services
        ;;
    rebuild)
        rebuild_all
        ;;
    *)
        echo "RAG System - Docker Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  build       Build Docker images"
        echo "  start       Start all services"
        echo "  stop        Stop all services"
        echo "  restart     Restart all services"
        echo "  logs        Show logs (follow)"
        echo "  status      Show service status and health"
        echo "  clean       Stop and remove containers"
        echo "  rebuild     Rebuild images and restart"
        echo ""
        echo "Examples:"
        echo "  $0 build       # First time setup"
        echo "  $0 start       # Start services"
        echo "  $0 logs        # View logs"
        echo "  $0 status      # Check health"
        exit 1
        ;;
esac
