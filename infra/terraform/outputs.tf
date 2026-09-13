output "ecs_cluster_name" { value = aws_ecs_cluster.this.name }
output "load_balancer_dns" { value = aws_lb.this.dns_name }
output "api_target_group_arn" { value = aws_lb_target_group.api.arn }
output "web_target_group_arn" { value = aws_lb_target_group.web.arn }
output "database_endpoint" { value = aws_db_instance.this.address }
output "redis_endpoint" { value = aws_elasticache_replication_group.this.primary_endpoint_address }
