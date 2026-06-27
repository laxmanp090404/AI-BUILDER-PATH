# AI Model Comparison – Lesson 1, Task 1

## Overview

This assignment evaluates and compares the capabilities of four Large Language Models (LLMs) across practical software engineering tasks relevant to Application Development, Data Engineering, and DevOps.

The comparison focuses on how each model performs on realistic enterprise-level prompts instead of simple coding questions. Each model was evaluated using the same prompts to ensure a fair comparison.

---

# Models Evaluated

| Model             | Access Method        |
| ----------------- | -------------------- |
| GPT-4o            | ChatGPT              |
| Claude Sonnet 4.6 | AWS Bedrock          |
| Gemini 2.5 Flash  | Google AI Studio     |
| DeepSeek-R1:7B    | Ollama (Local Model) |

---

# Local Environment

* **Machine:** MacBook Pro M1 Pro (2021)
* **Memory:** 16 GB RAM
* **Storage:** 512 GB SSD
* **Operating System:** macOS Tahoe 26.5.1

---

# Model Access Details

### GPT-4o

* Accessed using ChatGPT.

### Claude Sonnet 4.6

* Accessed through Amazon Bedrock.
* IAM user configured with Bedrock permissions.
* Model invoked through the Bedrock Playground.

### Gemini 2.5 Flash

* Accessed using Google AI Studio.
* Authenticated using a Google AI Studio API Key.

### DeepSeek-R1:7B

* Executed locally using Ollama.
* Model:

  ```
  deepseek-r1:7b
  ```

---

# Evaluation Use Cases

Three enterprise-oriented use cases were designed to benchmark the models.

## 1. Application Development

Production-grade backend API development using:

* Node.js
* Express
* PostgreSQL
* JWT Authentication
* Role-Based Authorization
* Layered Architecture
* Transactions
* Validation
* Error Handling

Evaluation focused on:

* Code Quality
* Architecture
* Security
* Maintainability
* Production Readiness

---

## 2. Data Engineering

Advanced PostgreSQL analytics involving:

* Complex SQL generation
* Aggregate queries
* Performance optimization
* Index recommendations
* Query explanations

Evaluation focused on:

* SQL correctness
* PostgreSQL features
* Optimization strategies
* Scalability

---

## 3. DevOps

Production-ready AWS Infrastructure using Terraform.

Requirements included:

* VPC
* Public & Private Subnets
* Internet Gateway
* NAT Gateway
* Application Load Balancer
* Auto Scaling Group
* EC2
* RDS PostgreSQL
* CloudWatch
* Modular Terraform

Evaluation focused on:

* Infrastructure design
* Security
* Terraform best practices
* Production readiness

---

# Evaluation Criteria

Each model was evaluated using the following criteria:

* Code Quality
* SQL Generation
* Infrastructure Automation
* Ease of Use
* Speed / Latency

Rating Scale:

* Excellent
* Good
* Basic
* Not Supported

---

# Notes

* The same prompts were used across all models to ensure consistency and fairness.
* The evaluation considered both correctness and production readiness rather than response length.
* Responses were manually reviewed for architecture, security, optimization techniques, maintainability, and adherence to best practices.
* Latency observations were based on interactive usage and are intended for comparative purposes rather than precise benchmarking.
* DeepSeek-R1:7B was evaluated as a local model running entirely on-device through Ollama without relying on cloud infrastructure.

---

# Repository Structure

```
Task-1/
│
├── UseCases/
│   ├── AppDev.txt
│   ├── Data.txt
│   └── DevOps.txt
│
├── Outputs/
│   ├── GPT4o/
│   ├── ClaudeSonnet/
│   ├── GeminiFlash/
│   └── DeepSeekR1/
│
├── Comparison.md
└── README.md
```

---

# Comparison Summary

The consolidated comparison table below summarizes the performance of all evaluated models across the three benchmark tasks.

| Model                       | Code Quality  | SQL Generation | Infra Automation | Ease of Use   | Speed / Latency | Comments                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------- | ------------- | -------------- | ---------------- | ------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **GPT-4o**                  | **Excellent** | **Excellent**  | **Excellent**    | **Excellent** | **Good**        | Produced clean, production-oriented solutions with well-structured layered architecture, optimized PostgreSQL queries, and modular Terraform code. Responses were concise, accurate, and required minimal manual refinement. Strong balance between implementation quality and readability.                                                                                                 |
| **Claude Sonnet 4.6**       | **Excellent** | **Excellent**  | **Excellent**    | **Good**      | **Good**        | Most comprehensive and production-ready outputs. Included advanced architectural decisions, detailed validation, audit logging, PostgreSQL optimization (partial indexes, covering indexes, materialized views), and enterprise-grade Terraform practices such as Secrets Manager, IMDSv2, remote state, and security hardening. Responses were more verbose but technically the strongest. |
| **Gemini 2.5 Flash**        | **Good**      | **Good**       | **Good**         | **Excellent** | **Excellent**   | Generated accurate and well-organized solutions with strong foundational architecture. Excelled in response speed and usability. While technically correct, it generally omitted advanced production optimizations, deeper security considerations, and enterprise-scale deployment practices found in GPT-4o and Claude.                                                                   |
| **DeepSeek-R1:7B (Ollama)** | **Basic**     | **Basic**      | **Basic**        | **Good**      | **Excellent**   | Demonstrated understanding of overall concepts but frequently generated incorrect syntax, hallucinated APIs, invalid Terraform resources, and SQL/logical errors. Suitable for simple reasoning and experimentation, but significant manual corrections are required before production use. Benefits from running completely offline with minimal latency.                                  |
