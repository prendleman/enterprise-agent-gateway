resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_ecs_cluster" "this" {
  name = "${local.name_prefix}-cluster"
  tags = local.common_tags

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb-sg"
  description = "ALB ingress for agent gateway"
  vpc_id      = var.vpc_id
  tags        = local.common_tags

  ingress {
    description = "HTTP from allowed CIDRs"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "ECS tasks for agent gateway"
  vpc_id      = var.vpc_id
  tags        = local.common_tags

  ingress {
    description     = "Traffic from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "api" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = local.common_tags
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name_prefix}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  tags        = local.common_tags

  health_check {
    enabled             = true
    path                = "/health/ready"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-exec"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "secrets_access" {
  count = (var.openai_secret_arn != "" || var.anthropic_secret_arn != "") ? 1 : 0
  name  = "${local.name_prefix}-secrets-read"
  role  = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
      ]
      Resource = compact([
        var.openai_secret_arn,
        var.anthropic_secret_arn,
      ])
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

locals {
  secret_env = compact([
    var.openai_secret_arn != "" ? {
      name      = "OPENAI_API_KEY"
      valueFrom = var.openai_secret_arn
    } : null,
    var.anthropic_secret_arn != "" ? {
      name      = "ANTHROPIC_API_KEY"
      valueFrom = var.anthropic_secret_arn
    } : null,
  ])
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  tags                     = local.common_tags

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.container_image
      essential = true
      portMappings = [{
        containerPort = var.container_port
        hostPort      = var.container_port
        protocol      = "tcp"
      }]
      environment = [
        { name = "APP_ENV", value = var.environment },
        { name = "DEMO_MODE", value = "true" },
        { name = "USE_FAKE_PROVIDERS", value = "true" },
        { name = "LOG_JSON", value = "true" },
      ]
      secrets = local.secret_env
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -fsS http://127.0.0.1:${var.container_port}/health/live || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    },
  ])
}

resource "aws_ecs_service" "api" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  tags            = local.common_tags

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.http]
}
