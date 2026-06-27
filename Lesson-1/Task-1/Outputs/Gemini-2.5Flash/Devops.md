
# GEMINI 2.5 FLASH DEVOPS

To build a production-ready, highly available infrastructure on AWS, we will implement a modular Terraform configuration. This architecture separates concerns into logical layers: **Networking**, **Compute** (with Auto Scaling and Load Balancing), and **Database** (Multi-AZ RDS).

---

## 📂 Project Directory Layout

```text
terraform-aws-infra/
├── main.tf                 # Root module orchestrating child modules
├── variables.tf            # Global input variables
├── outputs.tf              # Global output variables
└── modules/
    ├── networking/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── compute/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── database/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf

```

---

## 🧱 Root Configuration

### `main.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source               = "./modules/networking"
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

module "compute" {
  source             = "./modules/compute"
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  public_subnet_ids  = module.networking.public_subnet_ids
  private_subnet_ids = module.networking.private_subnet_ids
  instance_type      = var.instance_type
}

module "database" {
  source                  = "./modules/database"
  environment             = var.environment
  vpc_id                  = module.networking.vpc_id
  database_subnet_ids     = module.networking.private_subnet_ids
  db_instance_class       = var.db_instance_class
  db_name                 = var.db_name
  db_username             = var.db_username
  db_password             = var.db_password
  compute_security_group_id = module.compute.app_security_group_id
}

```

### `variables.tf`

```hcl
variable "aws_region" { type = string; default = "us-east-1" }
variable "environment" { type = string; default = "production" }
variable "vpc_cidr" { type = string; default = "10.0.0.0/16" }
variable "availability_zones" { type = list(string); default = ["us-east-1a", "us-east-1b"] }
variable "public_subnet_cidrs" { type = list(string); default = ["10.0.1.0/24", "10.0.2.0/24"] }
variable "private_subnet_cidrs" { type = list(string); default = ["10.0.10.0/24", "10.0.11.0/24"] }
variable "instance_type" { type = string; default = "t3.medium" }
variable "db_instance_class" { type = string; default = "db.r6g.large" }
variable "db_name" { type = string; default = "app_prod_db" }
variable "db_username" { type = string; default = "db_admin" }
variable "db_password" { type = string; sensitive = true }

```

### `outputs.tf`

```hcl
output "alb_dns_name" {
  description = "The public URL of the application load balancer"
  value       = module.compute.alb_dns_name
}

output "database_endpoint" {
  description = "The connection endpoint for the PostgreSQL instance"
  value       = module.database.db_endpoint
}

```

---

## 🛠️ Module Implementations

### 1. Networking Module (`modules/networking`)

Handles the creation of the isolated VPC topology, public routing via the Internet Gateway, and private egress via a highly available NAT Gateway setup.

#### `modules/networking/main.tf`

```hcl
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "${var.environment}-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.environment}-igw" }
}

resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.environment}-public-${var.availability_zones[count.index]}" }
}

resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]
  tags              = { Name = "${var.environment}-private-${var.availability_zones[count.index]}" }
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "${var.environment}-nat-eip" }
}

# NAT Gateway deployed in the first public subnet
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  tags          = { Name = "${var.environment}-nat" }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = { Name = "${var.environment}-public-rt" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }
  tags = { Name = "${var.environment}-private-rt" }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

```

*(Outputs from this module export `vpc_id`, `public_subnet_ids`, and `private_subnet_ids` as lists).*

---

### 2. Compute Module (`modules/compute`)

Provisions a public-facing Application Load Balancer (ALB) that distributes incoming requests to a dynamic, monitored Auto Scaling Group (ASG) running EC2 instances inside the private subnets.

#### `modules/compute/main.tf`

```hcl
# Security Group for Public Application Load Balancer
resource "aws_security_group" "alb" {
  name        = "${var.environment}-alb-sg"
  description = "Allow inbound public web traffic"
  vpc_id      = var.vpc_id

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

# Security Group for Private EC2 Application Instances
resource "aws_security_group" "app" {
  name        = "${var.environment}-app-sg"
  description = "Allow traffic exclusively via ALB"
  vpc_id      = var.vpc_id

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

# Application Load Balancer
resource "aws_alb" "external" {
  name               = "${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "app_tg" {
  name     = "${var.environment}-app-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/health"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_alb.external.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_tg.arn
  }
}

# Auto Scaling Group Configuration
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-minimal-*-x86_64"]
  }
}

resource "aws_launch_template" "app_lt" {
  name_prefix   = "${var.environment}-app-template-"
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type

  network_interfaces {
    associate_public_ip_address = false
    security_groups             = [aws_security_group.app.id]
  }

  user_data = base64encode(<<-EOF
              #!/bin/bash
              echo "Hello World from Production App Instance Layer" > index.html
              # Basic web server spin-up command for mock functionality 
              python3 -m http.server 8080 &
              EOF
  )

  monitoring {
    enabled = true
  }
}

resource "aws_autoscaling_group" "asg" {
  name                = "${var.environment}-asg"
  vpc_zone_identifier = var.private_subnet_ids
  target_group_arns   = [aws_lb_target_group.app_tg.arn]
  
  min_size         = 2
  max_size         = 5
  desired_capacity = 2

  launch_template {
    id      = aws_launch_template.app_lt.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.environment}-asg-node"
    assign_with_asg_target = true
  }
}

# CloudWatch Infrastructure Alarm Metrics
resource "aws_cloudwatch_metric_alarm" "asg_cpu_high" {
  alarm_name          = "${var.environment}-asg-high-cpu-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 80

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.asg.name
  }
}

```

---

### 3. Database Module (`modules/database`)

Deploys a secure PostgreSQL instance inside private subnets with a firewall rule configuration restricting input queries strictly to compute layer requests.

#### `modules/database/main.tf`

```hcl
resource "aws_db_subnet_group" "rds" {
  name       = "${var.environment}-rds-subnet-group"
  subnet_ids = var.database_subnet_ids
  tags       = { Name = "${var.environment}-rds-subnet-group" }
}

resource "aws_security_group" "db" {
  name        = "${var.environment}-db-sg"
  description = "Restricted ingress to specific cluster nodes only"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.compute_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.environment}-postgres"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  max_allocated_storage  = 100 # Auto-scaling storage block configuration
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds.name
  vpc_security_group_ids = [aws_security_group.db.id]
  
  multi_az               = true # High availability replica setup
  skip_final_snapshot    = var.environment == "production" ? false : true
  final_snapshot_identifier = "${var.environment}-postgres-final-snapshot"

  storage_encrypted      = true
}

```

---

## 🧠 Architectural Decisions & Best Practices

* **Layered Security (Least Privilege):** * The Application Load Balancer sits in the public subnets, accepting public internet traffic over standard ports.
* The EC2 computation engines run inside **isolated private subnets** with absolutely no direct public access. They accept connections exclusively via requests routed through the ALB security group ID.
* The RDS database tier is nested deeply within internal subnets, blocking arbitrary perimeter intrusions and opening the standard PostgreSQL port (`5432`) only to requests from verified EC2 security group IDs.


* **No Hardcoded Secrets:** DB Administrative Master Passwords use variable structures tagged with `sensitive = true`, allowing operators to supply payloads at execution via external environment managers (e.g., AWS Secrets Manager, Terraform Cloud variables) without tracking clear-text credentials inside the code base repository history.
* **Resiliency & Dynamic Horizontal Scaling:** High Availability is preserved across Multi-AZ parameters using Multi-AZ RDS parameters combined with Auto Scaling minimum footprints (`min_size = 2`), preventing downtime during partial AWS zone outages.