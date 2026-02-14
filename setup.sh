#!/bin/bash
# setup.sh - Setup script for netboot-orchestrator

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  RPi Netboot Orchestrator - Initial Setup              ║"
echo "╚════════════════════════════════════════════════════════╝"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

echo "✓ Docker found: $(docker --version)"

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker Compose found: $(docker-compose --version)"

# Create .env from .env.example if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ .env file created. Edit it if needed."
else
    echo "✓ .env file already exists"
fi

# Create data directory
echo ""
echo "📁 Creating data directories..."
mkdir -p data/{http/{raspi/kernels/{default,test},os,ipxe},tftp/{raspi,pxe},iscsi/images}
echo "✓ Data directories created"

# Show next steps
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Setup Complete! Next Steps:                           ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║  1. Edit .env file with your configuration             ║"
echo "║  2. Run: docker-compose up -d                          ║"
echo "║  3. Access UI: http://localhost:3000                   ║"
echo "║  4. API Docs: http://localhost:8000/docs               ║"
echo "╚════════════════════════════════════════════════════════╝"
