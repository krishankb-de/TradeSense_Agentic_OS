#!/bin/bash
# TradeSense Azure Deployment Script
# Uses Azure for Students $100 credit
# Deploys: App Service + PostgreSQL + Redis + Azure OpenAI + Azure Speech

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-tradesense-rg}"
LOCATION="${LOCATION:-eastus}"
APP_NAME="${APP_NAME:-tradesense}"
SKU="${SKU:-B1}"  # B1 = Basic tier, ~$13/month

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}TradeSense Azure Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Login to Azure
echo -e "${YELLOW}Logging in to Azure...${NC}"
az login

# Create resource group
echo -e "${YELLOW}Creating resource group: ${RESOURCE_GROUP}${NC}"
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}"

# Create App Service Plan
echo -e "${YELLOW}Creating App Service Plan...${NC}"
az appservice plan create \
  --name "${APP_NAME}-plan" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --is-linux \
  --sku "${SKU}"

# Create PostgreSQL Flexible Server
echo -e "${YELLOW}Creating PostgreSQL Flexible Server...${NC}"
POSTGRES_PASSWORD=$(openssl rand -base64 32)
az postgres flexible-server create \
  --name "${APP_NAME}-postgres" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --admin-user tradesenseadmin \
  --admin-password "${POSTGRES_PASSWORD}" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 15 \
  --public-access 0.0.0.0

# Create database
echo -e "${YELLOW}Creating database...${NC}"
az postgres flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${APP_NAME}-postgres" \
  --database-name tradesense

# Create Redis Cache
echo -e "${YELLOW}Creating Redis Cache...${NC}"
az redis create \
  --name "${APP_NAME}-redis" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Basic \
  --vm-size c0 \
  --enable-non-ssl-port false

# Get Redis connection info
REDIS_KEY=$(az redis list-keys \
  --name "${APP_NAME}-redis" \
  --resource-group "${RESOURCE_GROUP}" \
  --query primaryKey -o tsv)

REDIS_HOST=$(az redis show \
  --name "${APP_NAME}-redis" \
  --resource-group "${RESOURCE_GROUP}" \
  --query hostName -o tsv)

# Create Azure OpenAI resource
echo -e "${YELLOW}Creating Azure OpenAI resource...${NC}"
az cognitiveservices account create \
  --name "${APP_NAME}-openai" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --kind OpenAI \
  --sku S0 \
  --yes

# Deploy GPT-4 model
echo -e "${YELLOW}Deploying GPT-4 model...${NC}"
az cognitiveservices account deployment create \
  --name "${APP_NAME}-openai" \
  --resource-group "${RESOURCE_GROUP}" \
  --deployment-name gpt-4 \
  --model-name gpt-4 \
  --model-version "0613" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard"

# Get OpenAI keys
OPENAI_KEY=$(az cognitiveservices account keys list \
  --name "${APP_NAME}-openai" \
  --resource-group "${RESOURCE_GROUP}" \
  --query key1 -o tsv)

OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name "${APP_NAME}-openai" \
  --resource-group "${RESOURCE_GROUP}" \
  --query properties.endpoint -o tsv)

# Create Azure Speech Services
echo -e "${YELLOW}Creating Azure Speech Services...${NC}"
az cognitiveservices account create \
  --name "${APP_NAME}-speech" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --kind SpeechServices \
  --sku S0 \
  --yes

# Get Speech keys
SPEECH_KEY=$(az cognitiveservices account keys list \
  --name "${APP_NAME}-speech" \
  --resource-group "${RESOURCE_GROUP}" \
  --query key1 -o tsv)

# Create Web App
echo -e "${YELLOW}Creating Web App...${NC}"
az webapp create \
  --name "${APP_NAME}-backend" \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_NAME}-plan" \
  --deployment-container-image-name tradesense/backend:latest

# Configure Web App settings
echo -e "${YELLOW}Configuring Web App settings...${NC}"
az webapp config appsettings set \
  --name "${APP_NAME}-backend" \
  --resource-group "${RESOURCE_GROUP}" \
  --settings \
    ENVIRONMENT=production \
    DATABASE_URL="postgresql://tradesenseadmin:${POSTGRES_PASSWORD}@${APP_NAME}-postgres.postgres.database.azure.com:5432/tradesense?sslmode=require" \
    REDIS_URL="rediss://${REDIS_HOST}:6380?password=${REDIS_KEY}&ssl=true" \
    AZURE_OPENAI_KEY="${OPENAI_KEY}" \
    AZURE_OPENAI_ENDPOINT="${OPENAI_ENDPOINT}" \
    AZURE_SPEECH_KEY="${SPEECH_KEY}" \
    AZURE_SPEECH_REGION="${LOCATION}" \
    USE_AZURE_OPENAI=true \
    USE_AZURE_SPEECH=true

# Enable HTTPS only
az webapp update \
  --name "${APP_NAME}-backend" \
  --resource-group "${RESOURCE_GROUP}" \
  --https-only true

# Get Web App URL
WEB_APP_URL=$(az webapp show \
  --name "${APP_NAME}-backend" \
  --resource-group "${RESOURCE_GROUP}" \
  --query defaultHostName -o tsv)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Web App URL:${NC} https://${WEB_APP_URL}"
echo -e "${GREEN}PostgreSQL Host:${NC} ${APP_NAME}-postgres.postgres.database.azure.com"
echo -e "${GREEN}Redis Host:${NC} ${REDIS_HOST}"
echo ""
echo -e "${YELLOW}Save these credentials securely:${NC}"
echo "PostgreSQL Password: ${POSTGRES_PASSWORD}"
echo "Redis Key: ${REDIS_KEY}"
echo "OpenAI Key: ${OPENAI_KEY}"
echo "Speech Key: ${SPEECH_KEY}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Build and push Docker image: docker build -t tradesense/backend:latest backend/"
echo "2. Push to registry: docker push tradesense/backend:latest"
echo "3. Restart web app: az webapp restart --name ${APP_NAME}-backend --resource-group ${RESOURCE_GROUP}"
echo ""
echo -e "${GREEN}Estimated monthly cost: ~$50-70 (covered by $100 student credit)${NC}"
