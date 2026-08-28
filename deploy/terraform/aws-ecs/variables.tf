variable "aws_region" {
  description = "AWS region for ECS deployment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Portfolio project slug used in resource naming."
  type        = string
  default     = "agent-gateway"
}

variable "environment" {
  description = "Deployment environment label (e.g. demo, staging)."
  type        = string
  default     = "demo"
}

variable "vpc_id" {
  description = "Existing VPC ID (not created by this module)."
  type        = string
}

variable "private_subnet_ids" {
  description = "Existing private subnet IDs for ECS tasks."
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Existing public subnet IDs for the ALB."
  type        = list(string)
}

variable "container_image" {
  description = "Container image URI for the agent gateway API."
  type        = string
  default     = "enterprise-agent-gateway:latest"
}

variable "container_port" {
  description = "Container port exposed by the API."
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Desired ECS task count."
  type        = number
  default     = 2
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 1024
}

variable "openai_secret_arn" {
  description = "Secrets Manager ARN for OpenAI API key (input only)."
  type        = string
  default     = ""
}

variable "anthropic_secret_arn" {
  description = "Secrets Manager ARN for Anthropic API key (input only)."
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Additional resource tags."
  type        = map(string)
  default     = {}
}
