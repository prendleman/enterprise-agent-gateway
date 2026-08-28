# AWS ECS Fargate — Portfolio Example

Validation-ready Terraform for deploying the **Enterprise Agent Gateway** portfolio platform onto **existing** AWS networking. This module does **not** claim production deployment; it demonstrates how you would wire ECS Fargate, an ALB, CloudWatch Logs, and Secrets Manager ARNs.

## Prerequisites

- Terraform >= 1.5
- Existing VPC, public subnets (ALB), and private subnets (ECS tasks)
- Container image published to ECR (or another registry)
- Optional: Secrets Manager secrets for provider API keys

## Validate locally

```bash
cd deploy/terraform/aws-ecs
terraform init -backend=false
terraform fmt -check
terraform validate
```

Use `terraform.tfvars.example` as a template. Replace placeholder VPC/subnet IDs and secret ARNs before any real `plan` or `apply`.

## Inputs (high level)

| Variable | Purpose |
|----------|---------|
| `vpc_id` | Existing VPC — not created here |
| `private_subnet_ids` | ECS task placement |
| `public_subnet_ids` | Internet-facing ALB |
| `openai_secret_arn` / `anthropic_secret_arn` | Secrets Manager ARNs only |
| `container_image` | ECR image URI |

## What this creates

- ECS cluster + Fargate service (2 tasks by default)
- Application Load Balancer with `/health/ready` checks
- CloudWatch log group with configurable retention
- IAM execution role with optional Secrets Manager read policy
- Security groups restricting task ingress to ALB

## What this does not create

- VPC, subnets, NAT gateways, or Route53 records
- Secrets or secret values
- WAF, mTLS, or private connectivity patterns

See `docs/architecture.md` for the full portfolio architecture narrative.
