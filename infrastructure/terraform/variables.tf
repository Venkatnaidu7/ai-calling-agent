variable "do_token" { type = string sensitive = true }
variable "environment" { type = string default = "staging" }
variable "region" { type = string default = "blr1" }
variable "droplet_size" { type = string default = "s-2vcpu-4gb" }
variable "ssh_key_ids" { type = list(string) }
variable "allowed_ssh_cidrs" { type = list(string) default = [] }
variable "domain" { type = string default = "" }
