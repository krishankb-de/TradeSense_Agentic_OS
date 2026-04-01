# TradeSense DigitalOcean Infrastructure as Code
# Terraform configuration for DigitalOcean deployment
# Uses DigitalOcean $200 student credit

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

# ============================================================================
# Variables
# ============================================================================

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "tradesense"
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc3"
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "droplet_size" {
  description = "Droplet size"
  type        = string
  default     = "s-1vcpu-1gb"  # $6/month
}

variable "postgres_size" {
  description = "PostgreSQL database size"
  type        = string
  default     = "db-s-1vcpu-1gb"  # $15/month
}

variable "redis_size" {
  description = "Redis database size"
  type        = string
  default     = "db-s-1vcpu-1gb"  # $15/month
}

variable "azure_openai_key" {
  description = "Azure OpenAI API key"
  type        = string
  sensitive   = true
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint"
  type        = string
}

variable "azure_speech_key" {
  description = "Azure Speech Services API key"
  type        = string
  sensitive   = true
}

variable "azure_speech_region" {
  description = "Azure Speech Services region"
  type        = string
  default     = "eastus"
}

# ============================================================================
# PostgreSQL Database Cluster
# ============================================================================

resource "digitalocean_database_cluster" "postgres" {
  name       = "${var.app_name}-postgres"
  engine     = "pg"
  version    = "15"
  size       = var.postgres_size
  region     = var.region
  node_count = 1
  
  tags = [var.environment, "terraform", "tradesense"]
}

resource "digitalocean_database_db" "tradesense" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "tradesense"
}

resource "digitalocean_database_user" "tradesense" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "tradesense"
}

# ============================================================================
# Redis Database Cluster
# ============================================================================

resource "digitalocean_database_cluster" "redis" {
  name       = "${var.app_name}-redis"
  engine     = "redis"
  version    = "7"
  size       = var.redis_size
  region     = var.region
  node_count = 1
  
  tags = [var.environment, "terraform", "tradesense"]
}

# ============================================================================
# Droplet (Virtual Machine)
# ============================================================================

resource "digitalocean_ssh_key" "default" {
  name       = "${var.app_name}-ssh-key"
  public_key = file("~/.ssh/id_rsa.pub")
}

resource "digitalocean_droplet" "backend" {
  name   = "${var.app_name}-backend"
  region = var.region
  size   = var.droplet_size
  image  = "docker-20-04"
  
  ssh_keys = [digitalocean_ssh_key.default.fingerprint]
  
  tags = [var.environment, "terraform", "tradesense", "backend"]
  
  user_data = templatefile("${path.module}/cloud-init.yaml", {
    app_name              = var.app_name
    database_url          = digitalocean_database_cluster.postgres.uri
    redis_url             = digitalocean_database_cluster.redis.uri
    azure_openai_key      = var.azure_openai_key
    azure_openai_endpoint = var.azure_openai_endpoint
    azure_speech_key      = var.azure_speech_key
    azure_speech_region   = var.azure_speech_region
  })
}

# ============================================================================
# Firewall
# ============================================================================

resource "digitalocean_firewall" "backend" {
  name = "${var.app_name}-firewall"
  
  droplet_ids = [digitalocean_droplet.backend.id]
  
  # Allow HTTP
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  
  # Allow HTTPS
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  
  # Allow SSH
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  
  # Allow all outbound
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# ============================================================================
# Load Balancer (Optional - for production)
# ============================================================================

resource "digitalocean_loadbalancer" "backend" {
  count = var.environment == "production" ? 1 : 0
  
  name   = "${var.app_name}-lb"
  region = var.region
  
  forwarding_rule {
    entry_port     = 443
    entry_protocol = "https"
    
    target_port     = 80
    target_protocol = "http"
    
    certificate_name = digitalocean_certificate.cert[0].name
  }
  
  forwarding_rule {
    entry_port     = 80
    entry_protocol = "http"
    
    target_port     = 80
    target_protocol = "http"
  }
  
  healthcheck {
    port     = 80
    protocol = "http"
    path     = "/health"
  }
  
  droplet_ids = [digitalocean_droplet.backend.id]
}

# ============================================================================
# SSL Certificate (Optional - for production)
# ============================================================================

resource "digitalocean_certificate" "cert" {
  count = var.environment == "production" ? 1 : 0
  
  name    = "${var.app_name}-cert"
  type    = "lets_encrypt"
  domains = ["${var.app_name}.yourdomain.com"]
}

# ============================================================================
# Outputs
# ============================================================================

output "droplet_ip" {
  description = "Public IP address of the droplet"
  value       = digitalocean_droplet.backend.ipv4_address
}

output "postgres_uri" {
  description = "PostgreSQL connection URI"
  value       = digitalocean_database_cluster.postgres.uri
  sensitive   = true
}

output "postgres_host" {
  description = "PostgreSQL host"
  value       = digitalocean_database_cluster.postgres.host
}

output "postgres_port" {
  description = "PostgreSQL port"
  value       = digitalocean_database_cluster.postgres.port
}

output "redis_uri" {
  description = "Redis connection URI"
  value       = digitalocean_database_cluster.redis.uri
  sensitive   = true
}

output "redis_host" {
  description = "Redis host"
  value       = digitalocean_database_cluster.redis.host
}

output "load_balancer_ip" {
  description = "Load balancer IP address"
  value       = var.environment == "production" ? digitalocean_loadbalancer.backend[0].ip : null
}

output "ssh_command" {
  description = "SSH command to connect to droplet"
  value       = "ssh root@${digitalocean_droplet.backend.ipv4_address}"
}
