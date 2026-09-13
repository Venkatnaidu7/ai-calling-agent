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
variable "secret_key_arn" { type = string }
variable "openai_api_key_arn" { type = string }
variable "twilio_account_sid_arn" { type = string default = "" }
variable "twilio_auth_token_arn" { type = string default = "" }
variable "plivo_auth_id_arn" { type = string default = "" }
variable "plivo_auth_token_arn" { type = string default = "" }
variable "stripe_secret_key_arn" { type = string }
variable "stripe_webhook_secret_arn" { type = string }
variable "public_base_url" { type = string }
variable "frontend_url" { type = string }
variable "api_cpu" { type = number default = 512 }
variable "api_memory" { type = number default = 1024 }
variable "worker_cpu" { type = number default = 512 }
variable "worker_memory" { type = number default = 1024 }
