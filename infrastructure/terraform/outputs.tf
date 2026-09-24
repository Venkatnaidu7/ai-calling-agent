output "droplet_id" { value = digitalocean_droplet.app.id }
output "droplet_ipv4" { value = digitalocean_droplet.app.ipv4_address }
output "droplet_ipv6" { value = digitalocean_droplet.app.ipv6_address }
output "deployment_hostname" { value = var.domain != "" ? var.domain : digitalocean_droplet.app.ipv4_address }
