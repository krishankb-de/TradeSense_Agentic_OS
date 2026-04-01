# TradeSense Azure Infrastructure as Code
# Terraform configuration for Azure deployment
# Uses Azure for Students $100 credit

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# ============================================================================
# Variables
# ============================================================================

variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "tradesense"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "app_service_sku" {
  description = "App Service Plan SKU"
  type        = string
  default     = "B1"  # Basic tier, ~$13/month
}

variable "postgres_sku" {
  description = "PostgreSQL SKU"
  type        = string
  default     = "B_Standard_B1ms"  # Burstable tier, ~$12/month
}

variable "redis_sku" {
  description = "Redis Cache SKU"
  type        = string
  default     = "Basic"
}

variable "redis_capacity" {
  description = "Redis Cache capacity"
  type        = number
  default     = 0  # C0, ~$16/month
}

variable "azure_openai_key" {
  description = "Azure OpenAI API key"
  type        = string
  sensitive   = true
}

variable "azure_speech_key" {
  description = "Azure Speech Services API key"
  type        = string
  sensitive   = true
}

# ============================================================================
# Resource Group
# ============================================================================

resource "azurerm_resource_group" "main" {
  name     = "${var.app_name}-${var.environment}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "TradeSense"
  }
}

# ============================================================================
# PostgreSQL Flexible Server
# ============================================================================

resource "random_password" "postgres_password" {
  length  = 32
  special = true
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.app_name}-postgres"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  administrator_login    = "tradesenseadmin"
  administrator_password = random_password.postgres_password.result
  
  storage_mb = 32768  # 32 GB
  sku_name   = var.postgres_sku
  
  backup_retention_days = 7
  geo_redundant_backup_enabled = false
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "tradesense"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ============================================================================
# Redis Cache
# ============================================================================

resource "azurerm_redis_cache" "main" {
  name                = "${var.app_name}-redis"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = var.redis_capacity
  family              = "C"
  sku_name            = var.redis_sku
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  
  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# App Service Plan
# ============================================================================

resource "azurerm_service_plan" "main" {
  name                = "${var.app_name}-plan"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.app_service_sku
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# App Service (Web App)
# ============================================================================

resource "azurerm_linux_web_app" "main" {
  name                = "${var.app_name}-backend"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main.id
  https_only          = true
  
  site_config {
    always_on = true
    
    application_stack {
      docker_image     = "tradesense/backend"
      docker_image_tag = "latest"
    }
    
    ftps_state       = "Disabled"
    minimum_tls_version = "1.2"
  }
  
  app_settings = {
    ENVIRONMENT                    = var.environment
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    DOCKER_REGISTRY_SERVER_URL     = "https://index.docker.io"
    
    # Database
    DATABASE_URL = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}:${random_password.postgres_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.main.name}?sslmode=require"
    
    # Redis
    REDIS_URL = "rediss://${azurerm_redis_cache.main.hostname}:6380?password=${azurerm_redis_cache.main.primary_access_key}&ssl=true"
    
    # Azure OpenAI
    AZURE_OPENAI_KEY      = var.azure_openai_key
    AZURE_OPENAI_ENDPOINT = "https://${var.app_name}-openai.openai.azure.com/"
    USE_AZURE_OPENAI      = "true"
    
    # Azure Speech
    AZURE_SPEECH_KEY    = var.azure_speech_key
    AZURE_SPEECH_REGION = var.location
    USE_AZURE_SPEECH    = "true"
  }
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Outputs
# ============================================================================

output "web_app_url" {
  description = "URL of the deployed web application"
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "postgres_host" {
  description = "PostgreSQL server hostname"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "postgres_password" {
  description = "PostgreSQL administrator password"
  value       = random_password.postgres_password.result
  sensitive   = true
}

output "redis_host" {
  description = "Redis cache hostname"
  value       = azurerm_redis_cache.main.hostname
}

output "redis_primary_key" {
  description = "Redis primary access key"
  value       = azurerm_redis_cache.main.primary_access_key
  sensitive   = true
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}
