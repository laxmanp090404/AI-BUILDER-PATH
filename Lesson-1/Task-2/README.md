# Lesson 1- Task-2 – Testing Model Performance with Larger Context

## Overview

This task evaluates how well different Large Language Models (LLMs) understand, retain, and utilize large contextual information while answering follow-up questions.

Instead of evaluating general knowledge, the focus is on determining whether a model can correctly interpret project-specific documentation and generate responses that strictly follow the provided context.

---

# Context Used

For this evaluation, the **Complaint & Grievance Redressal (CGR) Portal** project documentation was used as the contextual knowledge base.

The documentation included multiple project artifacts covering functional, architectural, database, and infrastructure aspects.

---

# Context Documents Provided

The following project documents were supplied to each model:

* Project Requirements Specification
* Database Schema
* Entity Relationships
* Complaint Workflow
* Complaint Status Lifecycle
* Escalation Rules
* SLA Rules
* User Roles & Permissions
* API Requirements
* Coding Standards
* Project Architecture
* Folder Structure
* Business Rules

Together, these documents formed the knowledge base used during evaluation.

---

# Objective

The objective was to determine whether the models could:

* Understand large project documentation
* Follow project-specific business rules
* Generate code according to the documented architecture
* Answer questions without hallucinating information
* Maintain consistency across multiple follow-up questions
* Use information spread across different sections of the documentation

---

# Test Methodology

Each model received the same project documentation before being asked a series of follow-up questions.

The questions required the models to retrieve relevant information from the provided context instead of relying on general knowledge.

Example tasks included:

* Explaining the complaint workflow
* Identifying user permissions based on roles
* Generating APIs following project architecture
* Writing SQL queries using the provided schema
* Explaining SLA and escalation logic
* Answering implementation-specific questions
* Following coding standards while generating code

---

# Evaluation Criteria

The models were assessed on the following aspects:

* Context Understanding
* Instruction Following
* Information Retrieval
* Consistency
* Accuracy
* Hallucination Resistance
* Code Generation based on Context

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

# Observations

* Cloud-hosted models demonstrated stronger long-context understanding and produced more consistent responses across multiple follow-up questions.
* Claude Sonnet and GPT-4o handled project-specific business rules with high accuracy and generated responses closely aligned with the provided documentation.
* Gemini 2.5 Flash followed the supplied context well but occasionally produced shorter or less detailed explanations.
* DeepSeek-R1:7B successfully answered straightforward questions from the documentation but struggled with complex reasoning across multiple sections and occasionally introduced information not present in the supplied context.

---

# Conclusion

This exercise demonstrated the importance of long-context capabilities for enterprise software development.

When working with large codebases or complex software projects such as the Complaint & Grievance Redressal (CGR) Portal, the ability to understand extensive documentation and consistently follow project-specific requirements is as important as general coding ability.

Long-context reasoning enables developers to generate implementations that remain aligned with business rules, architectural standards, and project documentation, making it a critical capability for real-world software engineering workflows.
