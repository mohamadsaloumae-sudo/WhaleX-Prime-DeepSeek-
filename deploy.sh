
---

### **الملف 39: `deploy.sh` (سكربت النشر على Plesk)**

```bash
#!/bin/bash

# WhaleX Prime - Deployment Script for Plesk (Hunters Germany)
# Usage: ./deploy.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐋 WhaleX Prime Deployment Script${NC}"
echo "=================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}Error: SECRET_KEY not set in .env${NC}"
    exit 1
fi

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose down

# Pull latest images
echo -e "${YELLOW}Pulling latest images...${NC}"
docker-compose pull

# Build and start
echo -e "${YELLOW}Building and starting services...${NC}"
docker-compose up -d --build

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose exec -T backend alembic upgrade head

# Check if services are running
echo -e "${YELLOW}Checking services status...${NC}"
docker-compose ps

# Show logs
echo -e "${GREEN}Deployment complete!${NC}"
echo "=================================="
echo -e "Frontend: ${GREEN}http://localhost${NC}"
echo -e "API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo "=================================="
echo -e "${YELLOW}View logs: docker-compose logs -f${NC}"