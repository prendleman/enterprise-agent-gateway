output "cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.this.name
}

output "service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.api.name
}

output "load_balancer_dns" {
  description = "Public ALB DNS name."
  value       = aws_lb.api.dns_name
}

output "log_group_name" {
  description = "CloudWatch log group for ECS tasks."
  value       = aws_cloudwatch_log_group.api.name
}

output "task_definition_arn" {
  description = "ECS task definition ARN."
  value       = aws_ecs_task_definition.api.arn
}

output "security_group_id" {
  description = "ECS task security group ID."
  value       = aws_security_group.ecs_tasks.id
}
