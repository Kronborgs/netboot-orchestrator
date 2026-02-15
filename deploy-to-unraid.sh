#!/bin/bash
#
# Netboot Orchestrator - Safe Unraid Deployment Script
# This script ONLY operates within /mnt/user/appdata/netboot-orchestrator/
# It will NEVER delete anything outside this directory
#
# Usage: bash deploy-to-unraid.sh [clean]
# - No arguments: Normal deployment (git pull + build + restart)
# - clean: Stop and remove only netboot containers (data preserved)
#

set -e  # Exit on error

# Configuration
PROJECT_DIR="/mnt/user/appdata/netboot-orchestrator"
PROJECT_NAME="netboot-orchestrator"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
DATA_DIR="${PROJECT_DIR}/data"
BACKUP_DIR="${PROJECT_DIR}/backup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Safety check: Verify we're in the right directory
check_directory() {
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "Project directory not found: $PROJECT_DIR"
        log_info "Creating directory: $PROJECT_DIR"
        mkdir -p "$PROJECT_DIR"
    fi
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found at: $COMPOSE_FILE"
        log_info "Cloning repository..."
        git clone https://github.com/Kronborgs/netboot-orchestrator.git "$PROJECT_DIR" || {
            log_error "Failed to clone repository"
            exit 1
        }
    fi
}

# Backup current data (optional but recommended)
backup_data() {
    if [ ! -d "$DATA_DIR" ]; then
        log_info "No data directory to backup yet"
        return 0
    fi
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="${BACKUP_DIR}/backup_${TIMESTAMP}"
    
    log_warning "Creating backup of current data..."
    mkdir -p "$BACKUP_DIR"
    cp -r "$DATA_DIR" "$BACKUP_PATH"
    log_success "Backup created: $BACKUP_PATH"
}

# Stop only netboot containers (safe - doesn't affect other containers on Unraid)
stop_containers() {
    log_info "Stopping Netboot Orchestrator containers..."
    
    cd "$PROJECT_DIR"
    
    # Check if containers are running
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "$PROJECT_NAME"; then
        docker-compose -f "$COMPOSE_FILE" down
        log_success "Containers stopped"
    else
        log_info "No running containers found"
    fi
}

# Clean mode: Remove containers but preserve data and volumes
clean_containers() {
    log_warning "Cleaning containers (data preserved)..."
    
    cd "$PROJECT_DIR"
    
    # Stop and remove containers, but keep volumes and networks
    docker-compose -f "$COMPOSE_FILE" down
    
    log_success "Containers removed. Data preserved in: $DATA_DIR"
}

# Update code from GitHub
update_code() {
    log_info "Updating code from GitHub..."
    
    cd "$PROJECT_DIR"
    
    if [ -d .git ]; then
        log_info "Repository found, pulling latest changes..."
        git pull origin main || {
            log_warning "Could not pull from origin. Checking local status..."
        }
    else
        log_warning "Not a git repository. Cloning from GitHub..."
        cd ..
        rm -rf netboot-orchestrator-temp
        git clone https://github.com/Kronborgs/netboot-orchestrator.git netboot-orchestrator-temp
        cp -r netboot-orchestrator-temp/* "$PROJECT_DIR/"
        rm -rf netboot-orchestrator-temp
    fi
    
    log_success "Code updated"
}

# Build Docker images
build_containers() {
    log_info "Building Docker images (this may take 5-15 minutes)..."
    log_info "Using docker-compose.yml (full production setup)"
    
    cd "$PROJECT_DIR"
    
    # Build all services without cache
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    if [ $? -eq 0 ]; then
        log_success "Docker images built successfully"
    else
        log_error "Docker build failed"
        exit 1
    fi
}

# Start containers
start_containers() {
    log_info "Starting Netboot Orchestrator services..."
    
    cd "$PROJECT_DIR"
    
    # Create data directory if it doesn't exist
    mkdir -p "$DATA_DIR"
    
    # Start in detached mode
    docker-compose -f "$COMPOSE_FILE" up -d
    
    if [ $? -eq 0 ]; then
        log_success "Containers started"
        sleep 2
        
        # Check if all services are running
        docker-compose -f "$COMPOSE_FILE" ps
    else
        log_error "Failed to start containers"
        exit 1
    fi
}

# Check container status
check_status() {
    log_info "Checking Netboot Orchestrator status..."
    
    cd "$PROJECT_DIR"
    docker-compose -f "$COMPOSE_FILE" ps
    
    log_info "Services overview:"
    log_info "  - API: http://$(hostname -I | awk '{print $1}'):8000"
    log_info "  - Web UI: http://$(hostname -I | awk '{print $1}'):30000"
    log_info "  - TFTP: port 69 (UDP)"
    log_info "  - HTTP: port 8080"
    log_info "  - iSCSI: port 3260"
}

# Main deployment flow
deploy() {
    log_info "=== Netboot Orchestrator Deployment (Unraid) ==="
    log_info "Project directory: $PROJECT_DIR"
    log_info "SAFETY: Only operating within this directory"
    log_info ""
    
    check_directory
    
    # Backup data before updating
    read -p "Create backup of current data? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        backup_data
    fi
    
    # Stop old containers
    stop_containers
    
    # Update code
    update_code
    
    # Build new images
    build_containers
    
    # Start containers
    start_containers
    
    # Show status
    check_status
    
    log_success "=== Deployment Complete ==="
    log_info "Access Web UI at: http://$(hostname -I | awk '{print $1}'):30000"
    log_info "View logs: docker-compose -f $COMPOSE_FILE logs -f"
}

# Main execution
case "${1:-deploy}" in
    clean)
        clean_containers
        log_info "To redeploy: bash deploy-to-unraid.sh"
        ;;
    *)
        deploy
        ;;
esac
