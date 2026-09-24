locals {
  name = "ai-calling-${var.environment}"
}
resource "digitalocean_droplet" "app" {
  name = local.name
  region = var.region
  size = var.droplet_size
  image = "ubuntu-24-04-x64"
  ssh_keys = var.ssh_key_ids
  monitoring = true
  backups = true
  tags = ["ai-calling-agent", var.environment]
}
resource "digitalocean_firewall" "app" {
  name = "${local.name}-firewall"
  droplet_ids = [digitalocean_droplet.app.id]
  inbound_rule { protocol = "tcp" port_range = "22" source_addresses = var.allowed_ssh_cidrs }
  inbound_rule { protocol = "tcp" port_range = "80" source_addresses = ["0.0.0.0/0", "::/0"] }
  inbound_rule { protocol = "tcp" port_range = "443" source_addresses = ["0.0.0.0/0", "::/0"] }
  outbound_rule { protocol = "tcp" port_range = "1-65535" destination_addresses = ["0.0.0.0/0", "::/0"] }
  outbound_rule { protocol = "udp" port_range = "1-65535" destination_addresses = ["0.0.0.0/0", "::/0"] }
  outbound_rule { protocol = "icmp" destination_addresses = ["0.0.0.0/0", "::/0"] }
}
