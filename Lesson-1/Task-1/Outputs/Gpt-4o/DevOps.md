# GPT-4o DevOps
For a production-ready AWS deployment, I'd structure Terraform into reusable modules with clear separation of concerns:

```
terraform-aws-prod/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── terraform.tfvars
├── modules/
│   ├── networking/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── compute/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── database/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
```

---

# Root Module

## versions.tf

```hcl
terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
```

---

## variables.tf

```hcl
variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "prod"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "instance_type" {
  default = "t3.medium"
}

variable "db_username" {
  sensitive = true
}

variable "db_password" {
  sensitive = true
}
```

---

## main.tf

```hcl
module "networking" {
  source = "./modules/networking"

  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

module "compute" {
  source = "./modules/compute"

  environment         = var.environment
  vpc_id              = module.networking.vpc_id
  public_subnets      = module.networking.public_subnet_ids
  private_subnets     = module.networking.private_subnet_ids
}

module "database" {
  source = "./modules/database"

  environment         = var.environment
  vpc_id              = module.networking.vpc_id
  private_subnets     = module.networking.private_subnet_ids
  app_security_group  = module.compute.app_sg_id

  db_username         = var.db_username
  db_password         = var.db_password
}
```

---

## outputs.tf

```hcl
output "alb_dns_name" {
  value = module.compute.alb_dns_name
}

output "database_endpoint" {
  value = module.database.db_endpoint
}
```

---

# Networking Module

## modules/networking/variables.tf

```hcl
variable "environment" {}
variable "vpc_cidr" {}
```

---

## modules/networking/main.tf

```hcl
data "aws_availability_zones" "available" {}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.environment}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.environment}-public-${count.index}"
  }
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = local.azs[count.index]

  tags = {
    Name = "${var.environment}-private-${count.index}"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
}
```

### Routing

```hcl
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route" "internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route" "nat" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
}

resource "aws_route_table_association" "private" {
  count = 2

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
```

---

## modules/networking/outputs.tf

```hcl
output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}
```

---

# Compute Module

## modules/compute/variables.tf

```hcl
variable "environment" {}
variable "vpc_id" {}
variable "public_subnets" {}
variable "private_subnets" {}
```

---

## modules/compute/main.tf

### Security Groups

```hcl
resource "aws_security_group" "alb" {
  name   = "${var.environment}-alb-sg"
  vpc_id = var.vpc_id

  ingress {
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

resource "aws_security_group" "app" {
  name   = "${var.environment}-app-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 8080
    to_port         = 8080
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
```

---

### Launch Template

```hcl
data "aws_ami" "amazon_linux" {
  most_recent = true

  owners = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*"]
  }
}

resource "aws_launch_template" "app" {
  name_prefix   = "app-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = "t3.medium"

  vpc_security_group_ids = [
    aws_security_group.app.id
  ]

  monitoring {
    enabled = true
  }

  user_data = base64encode(<<EOF
#!/bin/bash
yum update -y
amazon-linux-extras install nginx1 -y
systemctl start nginx
systemctl enable nginx
EOF
)
}
```

---

### ALB

```hcl
resource "aws_lb" "app" {
  name               = "${var.environment}-alb"
  load_balancer_type = "application"

  security_groups = [
    aws_security_group.alb.id
  ]

  subnets = var.public_subnets
}

resource "aws_lb_target_group" "app" {
  name     = "${var.environment}-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path = "/"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
```

---

### Auto Scaling Group

```hcl
resource "aws_autoscaling_group" "app" {
  desired_capacity = 2
  min_size         = 2
  max_size         = 6

  vpc_zone_identifier = var.private_subnets

  target_group_arns = [
    aws_lb_target_group.app.arn
  ]

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  health_check_type = "ELB"
}
```

---

### CloudWatch Scaling

```hcl
resource "aws_autoscaling_policy" "cpu" {
  name                   = "cpu-scaling"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }

    target_value = 60
  }
}
```

---

## modules/compute/outputs.tf

```hcl
output "alb_dns_name" {
  value = aws_lb.app.dns_name
}

output "app_sg_id" {
  value = aws_security_group.app.id
}
```

---

# Database Module

## modules/database/variables.tf

```hcl
variable "environment" {}
variable "vpc_id" {}
variable "private_subnets" {}
variable "app_security_group" {}

variable "db_username" {}
variable "db_password" {
  sensitive = true
}
```

---

## modules/database/main.tf

### Security Group

```hcl
resource "aws_security_group" "db" {
  name   = "${var.environment}-db-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.app_security_group]
  }
}
```

---

### Subnet Group

```hcl
resource "aws_db_subnet_group" "db" {
  name       = "${var.environment}-db-subnets"
  subnet_ids = var.private_subnets
}
```

---

### PostgreSQL

```hcl
resource "aws_db_instance" "postgres" {
  identifier = "${var.environment}-postgres"

  engine         = "postgres"
  engine_version = "16"

  instance_class = "db.t3.medium"

  allocated_storage = 100
  storage_encrypted = true

  username = var.db_username
  password = var.db_password

  db_subnet_group_name = aws_db_subnet_group.db.name

  vpc_security_group_ids = [
    aws_security_group.db.id
  ]

  multi_az               = true
  backup_retention_period = 14
  deletion_protection     = true
  skip_final_snapshot     = false

  enabled_cloudwatch_logs_exports = [
    "postgresql"
  ]
}
```

---

## modules/database/outputs.tf

```hcl
output "db_endpoint" {
  value = aws_db_instance.postgres.endpoint
}
```

---

# Production Improvements Recommended

For a true enterprise-grade deployment, I'd additionally include:

1. **One NAT Gateway per AZ** (avoid single point of failure).
2. **HTTPS listener with ACM certificate**.
3. **AWS WAF** attached to ALB.
4. **Secrets Manager** for database credentials.
5. **KMS encryption** for EBS, RDS, and logs.
6. **CloudWatch dashboards and alarms** (CPU, memory, disk, RDS connections).
7. **VPC Flow Logs**.
8. **ALB access logging to S3**.
9. **RDS Performance Insights**.
10. **AWS Backup policies**.
11. **Terraform remote state** in S3 with DynamoDB locking.
12. **IAM roles and instance profiles** following least-privilege principles.
13. **Launch Template version pinning** and rolling instance refresh.
14. **Private EC2 instances only** (no public IPs).
15. **Route53 DNS records** for the ALB.

### Architecture Summary

```
Internet
    │
    ▼
Application Load Balancer
    │
    ▼
Auto Scaling Group
(EC2 in private subnets)
    │
    ▼
RDS PostgreSQL Multi-AZ
```

Network layout:

```
VPC
├── Public Subnet AZ1
│   ├── ALB
│   └── NAT Gateway
├── Public Subnet AZ2
│   └── ALB
├── Private Subnet AZ1
│   └── EC2
└── Private Subnet AZ2
    ├── EC2
    └── RDS
```

This design provides high availability across two Availability Zones, isolates application and database tiers in private subnets, supports horizontal scaling through an Auto Scaling Group, and includes managed load balancing, monitoring, and database resilience suitable for production workloads.
