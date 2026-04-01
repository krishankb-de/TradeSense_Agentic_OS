#!/bin/bash
# TradeSense DigitalOcean Deployment Script
# Uses DigitalOcean $200 student credit
# Estimated cost: ~$36/month

set -e

# Configuration
APP_NAME="${APP_NAME:-tradesense}"
REGION="${REGION:-nyc3}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}TradeSense DigitalOcean Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo -e "${RED}Error: doctl (DigitalOcean CLI) is not installed${NC}"
    echo "Install from: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Authenticate
echo -e "${YELLOW}Authenticating with DigitalOcean...${NC}"
doctl auth init

# Create PostgreSQL database
echo -e "${YELLOW}Creating PostgreSQL database cluster...${NC}"
doctl databases create "${APP_NAME}-postgres" \
  --engine pg \
  --version 15 \
  --region "${REGION}" \
  --size db-s-1vcpu-1gb \
  --num-nodes 1

# Wait for database to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
sleep 60

# Get database connection info
DB_ID=$(doctl databases list --format ID,Name --no-header | grep "${APP_NAME}-postgres" | awk '{print $1}')
DB_URI=$(doctl databases connection "${DB_ID}" --format URI --no-header)

# Create Redis database
echo -e "${YELLOW}Creating Redis database cluster...${NC}"
doctl databases create "${APP_NAME}-redis" \
  --engine redis \
  --version 7 \
  --region "${REGION}" \
  --size db-s-1vcpu-1gb \
  --num-nodes 1

# Wait for Redis to be ready
echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
sleep 60

# Get Redis connection info
REDIS_ID=$(doctl databases list --format ID,Name --no-header | grep "${APP_NAME}-redis" | awk '{print $1}')
REDIS_URI=$(doctl databases connection "${REDIS_ID}" --format URI --no-header)

# Create App Platform app
echo -e "${YELLOW}Creating App Platform application...${NC}"

# Check if app.yaml exists
if [ ! -f "deployment/digitalocean/app.yaml" ]; then
    echo -e "${RED}Error: app.yaml not found${NC}"
    exit 1
fi

# Deploy app
doctl apps create --spec deployment/digitalocean/app.yaml

# Get app ID
APP_ID=$(doctl apps list --format ID,Spec.Name --no-header | grep "${APP_NAME}" | awk '{print $1}')

# Set environment variables
echo -e "${YELLOW}Setting environment variables...${NC}"

# Prompt for Azure credentials
read -sp "Enter Azure OpenAI API Key: " AZURE_OPENAI_KEY
echo
read -p "Enter Azure OpenAI Endpoint: " AZURE_OPENAI_ENDPOINT
read -sp "Enter Azure Speech API Key: " AZURE_SPEECH_KEY
echo
read -p "Enter Azure Speech Region (e.g., eastus): " AZURE_SPEECH_REGION

# Optional: Datadog and Sentry
read -p "Enter Datadog API Key (optional, press Enter to skip): " DATADOG_API_KEY
read -p "Enter Sentry DSN (optional, press Enter to skip): " SENTRY_DSN

# Update app with environment variables
doctl apps update "${APP_ID}" --spec - <<EOF
name: ${APP_NAME}
region: ${REGION}

services:
  - name: backend
    envs:
      - key: DATABASE_URL
        value: ${DB_URI}
      - key: REDIS_URL
        value: ${REDIS_URI}
      - key: AZURE_OPENAI_KEY
        value: ${AZURE_OPENAI_KEY}
        type: SECRET
      - key: AZURE_OPENAI_ENDPOINT
        value: ${AZURE_OPENAI_ENDPOINT}
      - key: AZURE_SPEECH_KEY
        value: ${AZURE_SPEECH_KEY}
        type: SECRET
      - key: AZURE_SPEECH_REGION
        value: ${AZURE_SPEECH_REGION}
      - key: DATADOG_API_KEY
        value: ${DATADOG_API_KEY}
        type: SECRET
      - key: SENTRY_DSN
        value: ${SENTRY_DSN}
        type: SECRET
EOF

# Get app URL
APP_URL=$(doctl apps list --format ID,DefaultIngress --no-header | grep "${APP_ID}" | awk '{print $2}')

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}App URL:${NC} https://${APP_URL}"
echo -e "${GREEN}PostgreSQL:${NC} ${DB_URI}"
echo -e "${GREEN}Redis:${NC} ${REDIS_URI}"
echo ""
echo -e "${YELLOW}Monitor deployment:${NC}"
echo "doctl apps list"
echo "doctl apps logs ${APP_ID} --follow"
echo ""
echo -e "${GREEN}Estimated monthly cost: ~$36 (covered by $200 student credit)${NC}"
echo -e "${GREEN}Credit will last: ~5.5 months${NC}"
