data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  name = "${var.project_name}-${var.environment}"
}

resource "aws_ecs_cluster" "this" {
  name = local.name
  setting { name = "containerInsights" value = "enabled" }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name}/api"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${local.name}/worker"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${local.name}/web"
  retention_in_days = 30
}

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name}-ecs-execution"
  assume_role_policy = jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="ecs-tasks.amazonaws.com"},Action="sts:AssumeRole"}]})
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_security_group" "alb" {
  name   = "${local.name}-alb"
  vpc_id = var.vpc_id
  ingress { from_port = 443 to_port = 443 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  egress { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "app" {
  name   = "${local.name}-app"
  vpc_id = var.vpc_id
  ingress { from_port = 8000 to_port = 8000 protocol = "tcp" security_groups = [aws_security_group.alb.id] }
  ingress { from_port = 3000 to_port = 3000 protocol = "tcp" security_groups = [aws_security_group.alb.id] }
  egress { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "db" {
  name   = "${local.name}-db"
  vpc_id = var.vpc_id
  ingress { from_port = 5432 to_port = 5432 protocol = "tcp" security_groups = [aws_security_group.app.id] }
}

resource "aws_security_group" "redis" {
  name   = "${local.name}-redis"
  vpc_id = var.vpc_id
  ingress { from_port = 6379 to_port = 6379 protocol = "tcp" security_groups = [aws_security_group.app.id] }
}

resource "aws_db_subnet_group" "this" {
  name       = local.name
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_instance" "this" {
  identifier             = local.name
  engine                 = "postgres"
  engine_version         = "17"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  max_allocated_storage  = 100
  storage_encrypted      = true
  db_name                = var.database_name
  username               = var.database_username
  password               = var.database_password
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  backup_retention_period = 7
  deletion_protection    = true
  skip_final_snapshot    = false
}

resource "aws_elasticache_subnet_group" "this" {
  name       = local.name
  subnet_ids = var.private_subnet_ids
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id       = replace(local.name, "_", "-")
  description                = "Production Redis for ${local.name}"
  engine                     = "redis"
  engine_version             = "8.0"
  node_type                  = "cache.t4g.micro"
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [aws_security_group.redis.id]
}

resource "aws_lb" "this" {
  name               = substr(local.name, 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "api" {
  name        = substr("${local.name}-api", 0, 32)
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check { path = "/ready" port = "8000" }
}

resource "aws_lb_target_group" "web" {
  name        = substr("${local.name}-web", 0, 32)
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check { path = "/" port = "3000" }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  default_action { type = "forward" target_group_arn = aws_lb_target_group.web.arn }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  container_definitions = jsonencode([{
    name="api", image=var.api_image, essential=true,
    portMappings=[{containerPort=8000,protocol="tcp"}],
    environment=[
      {name="APP_ENV",value="production"},{name="API_HOST",value="0.0.0.0"},{name="API_PORT",value="8000"},
      {name="DATABASE_URL",value="postgresql+asyncpg://${var.database_username}:${var.database_password}@${aws_db_instance.this.address}:5432/${var.database_name}"},
      {name="REDIS_URL",value="redis://:${var.redis_auth_token}@${aws_elasticache_replication_group.this.primary_endpoint_address}:6379/0"},
      {name="PUBLIC_BASE_URL",value=var.public_base_url},{name="FRONTEND_URL",value=var.frontend_url},
      {name="CORS_ORIGINS",value=var.frontend_url},{name="TRUSTED_HOSTS",value="*"}
    ],
    secrets=[
      {name="SECRET_KEY",valueFrom=var.secret_key},{name="OPENAI_API_KEY",valueFrom=var.openai_api_key},
      {name="TWILIO_ACCOUNT_SID",valueFrom=var.twilio_account_sid},{name="TWILIO_AUTH_TOKEN",valueFrom=var.twilio_auth_token},
      {name="PLIVO_AUTH_ID",valueFrom=var.plivo_auth_id},{name="PLIVO_AUTH_TOKEN",valueFrom=var.plivo_auth_token},
      {name="STRIPE_SECRET_KEY",valueFrom=var.stripe_secret_key},{name="STRIPE_WEBHOOK_SECRET",valueFrom=var.stripe_webhook_secret}
    ],
    logConfiguration={logDriver="awslogs",options={awslogs-group=aws_cloudwatch_log_group.api.name,awslogs-region=var.aws_region,awslogs-stream-prefix="api"}}
  }])
}

resource "aws_ecs_service" "api" {
  name            = "api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  network_configuration { subnets=var.private_subnet_ids security_groups=[aws_security_group.app.id] assign_public_ip=false }
  load_balancer { target_group_arn=aws_lb_target_group.api.arn container_name="api" container_port=8000 }
  depends_on = [aws_lb_listener.https]
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${local.name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  container_definitions = jsonencode([{
    name="web", image=var.web_image, essential=true, portMappings=[{containerPort=3000,protocol="tcp"}],
    environment=[{name="NODE_ENV",value="production"},{name="NEXT_PUBLIC_API_URL",value="${var.public_base_url}/api/v1"}],
    logConfiguration={logDriver="awslogs",options={awslogs-group=aws_cloudwatch_log_group.web.name,awslogs-region=var.aws_region,awslogs-stream-prefix="web"}}
  }])
}

resource "aws_ecs_service" "web" {
  name="web" cluster=aws_ecs_cluster.this.id task_definition=aws_ecs_task_definition.web.arn desired_count=2 launch_type="FARGATE"
  network_configuration { subnets=var.private_subnet_ids security_groups=[aws_security_group.app.id] assign_public_ip=false }
  load_balancer { target_group_arn=aws_lb_target_group.web.arn container_name="web" container_port=3000 }
  depends_on=[aws_lb_listener.https]
}
