variable "aws_region" { type = string default = "ap-south-1" }
variable "project_name" { type = string default = "ai-calling-agent" }
variable "environment" { type = string default = "production" }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "certificate_arn" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "database_name" { type = string default = "voice" }
variable "database_username" { type = string default = "voice" }
variable "database_password" { type = string sensitive = true }
variable "redis_auth_token" { type = string sensitive = true }
variable "secret_key" { type = string sensitive = true }
variable "openai_api_key" { type = string sensitive = true }
variable "twilio_account_sid" { type = string sensitive = true default = "" }
variable "twilio_auth_token" { type = string sensitive = true default = "" }
variable "plivo_auth_id" { type = string sensitive = true default = "" }
variable "plivo_auth_token" { type = string sensitive = true default = "" }
variable "stripe_secret_key" { type = string sensitive = true }
variable "stripe_webhook_secret" { type = string sensitive = true }
variable "public_base_url" { type = string }
variable "frontend_url" { type = string }
variable "api_cpu" { type = number default = 512 }
variable "api_memory" { type = number default = 1024 }
variable "worker_cpu" { type = number default = 512 }
variable "worker_memory" { type = number default = 1024 }
