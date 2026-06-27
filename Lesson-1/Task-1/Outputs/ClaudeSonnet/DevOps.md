## CLAUDE SONNET 4.6 -  DEVOPS


I'll build this as a complete, modular Terraform project with separate files per module. Let me set up the structure and create each file.Now let's build out the networking module first.Now the compute module (ALB, ASG, Launch Template, IAM, CloudWatch alarms/scaling).Now the database module (RDS PostgreSQL, subnet group, parameter group, alarms).Now the root module that wires everything together.Let's validate the formatting/syntax with `terraform fmt` and `validate` if available.Terraform CLI isn't available in this sandbox to run automated validation, but I've kept resource references consistent across modules. Let me do a final structural check and package it up.All files have balanced braces. Now let's package everything for delivery.**Architecture summary:**

```
Internet → IGW → ALB (public subnets, 2 AZs)
                   ↓
         Auto Scaling Group / EC2 (private subnets, 2 AZs)
                   ↓
         RDS PostgreSQL Multi-AZ (isolated DB subnets, 2 AZs)
```

**Key design decisions** (full reasoning is in the README inside the zip):

- **3-tier subnetting per AZ** — public, private-app, and isolated-db subnets are kept separate so RDS has no route to the internet at all, not just a security group blocking it.
- **Security groups chain tier-to-tier** (ALB SG → EC2 SG → RDS SG), never raw CIDRs, so each layer only trusts the layer directly in front of it.
- **NAT Gateway per AZ by default** for HA, with a `single_nat_gateway` toggle for cost-sensitive/non-prod use.
- **SSM Session Manager instead of SSH** — no open port 22, full session audit logging, via IAM role on the launch template.
- **IMDSv2 enforced** on EC2 to close the SSRF→credential-theft path.
- **Target-tracking autoscaling on CPU** instead of manually-tuned step scaling.
- **RDS master password via Secrets Manager** (auto-generated/rotated, never in Terraform state or `.tfvars`), encrypted with a customer-managed KMS key.
- **RDS Multi-AZ, storage autoscaling, 14-day backups, deletion protection** — production-grade defaults.
- **CloudWatch alarms** on both tiers (ASG CPU, ALB 5xx/latency/unhealthy hosts; RDS CPU/memory/storage/connections/replica lag), all routed to one shared SNS topic.
- **S3 + DynamoDB remote state backend** with locking — required for production.

The zip contains the full module tree (`networking`, `compute`, `database`), root `main.tf`/`variables.tf`/`outputs.tf`/`providers.tf`, a `terraform.tfvars.example`, and a `README.md` with the architecture diagram, full rationale, and step-by-step usage instructions (including remote-state bootstrap). I wasn't able to run `terraform validate` in this sandbox (no Terraform binary / network access to install it), but I did check brace/block balance across all 17 `.tf` files by hand — run `terraform init && terraform validate` locally before applying.