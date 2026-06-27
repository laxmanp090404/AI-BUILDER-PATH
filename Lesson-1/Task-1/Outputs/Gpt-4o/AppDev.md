# GPT-4o APPDEV
Below is a production-oriented design and sample implementation for a **Complaint & Grievance Redressal API** using **Node.js, Express, PostgreSQL, JWT Authentication**, **Role-Based Access Control**, **Layered Architecture**, **Input Validation**, **Transactions**, and **Centralized Error Handling**.

---

# Project Structure

```text
src/
│
├── app.js
├── server.js
│
├── config/
│   ├── db.js
│   └── env.js
│
├── routes/
│   └── complaint.routes.js
│
├── controllers/
│   └── complaint.controller.js
│
├── services/
│   └── complaint.service.js
│
├── repositories/
│   └── complaint.repository.js
│
├── middleware/
│   ├── auth.middleware.js
│   ├── authorize.middleware.js
│   ├── validation.middleware.js
│   └── error.middleware.js
│
├── validations/
│   └── complaint.validation.js
│
├── utils/
│   ├── ApiError.js
│   └── constants.js
│
└── sql/
    └── schema.sql
```

---

# Database Schema

## schema.sql

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL
);

CREATE TABLE complaints (
    id UUID PRIMARY KEY,
    complaint_no VARCHAR(50) UNIQUE NOT NULL,
    employee_id UUID NOT NULL REFERENCES users(id),
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    priority VARCHAR(30) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE complaint_attachments (
    id UUID PRIMARY KEY,
    complaint_id UUID NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    mime_type VARCHAR(100),
    file_size BIGINT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_complaint_employee
ON complaints(employee_id);

CREATE INDEX idx_complaint_status
ON complaints(status);
```

---

# Environment Configuration

## config/env.js

```javascript
require("dotenv").config();

module.exports = {
  PORT: process.env.PORT,
  JWT_SECRET: process.env.JWT_SECRET,
  DATABASE_URL: process.env.DATABASE_URL
};
```

---

# PostgreSQL Connection Pool

## config/db.js

```javascript
const { Pool } = require("pg");
const env = require("./env");

const pool = new Pool({
  connectionString: env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000
});

module.exports = pool;
```

---

# Roles

## utils/constants.js

```javascript
const ROLES = {
  EMPLOYEE: "EMPLOYEE",
  GRO: "GRO",
  DEPARTMENT_HEAD: "DEPARTMENT_HEAD",
  ADMIN: "ADMIN"
};

module.exports = { ROLES };
```

---

# Custom Error Class

## utils/ApiError.js

```javascript
class ApiError extends Error {
  constructor(statusCode, message) {
    super(message);
    this.statusCode = statusCode;
  }
}

module.exports = ApiError;
```

---

# JWT Authentication Middleware

## middleware/auth.middleware.js

```javascript
const jwt = require("jsonwebtoken");
const env = require("../config/env");

module.exports = (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader?.startsWith("Bearer ")) {
      return res.status(401).json({
        success: false,
        message: "Authentication required"
      });
    }

    const token = authHeader.split(" ")[1];

    const decoded = jwt.verify(token, env.JWT_SECRET);

    req.user = decoded;

    next();
  } catch (err) {
    return res.status(401).json({
      success: false,
      message: "Invalid token"
    });
  }
};
```

---

# Role Authorization Middleware

## middleware/authorize.middleware.js

```javascript
module.exports = (...roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({
        success: false,
        message: "Access denied"
      });
    }

    next();
  };
};
```

---

# Validation

Install:

```bash
npm install express-validator
```

## validations/complaint.validation.js

```javascript
const { body } = require("express-validator");

exports.createComplaintValidation = [
  body("subject")
    .trim()
    .notEmpty()
    .withMessage("Subject is required")
    .isLength({ max: 255 }),

  body("description")
    .trim()
    .notEmpty()
    .withMessage("Description is required")
    .isLength({ min: 10 }),

  body("category")
    .trim()
    .notEmpty()
    .withMessage("Category is required"),

  body("priority")
    .optional()
    .isIn(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),

  body("attachments")
    .optional()
    .isArray()
];
```

---

# Validation Middleware

## middleware/validation.middleware.js

```javascript
const { validationResult } = require("express-validator");

module.exports = (req, res, next) => {
  const errors = validationResult(req);

  if (!errors.isEmpty()) {
    return res.status(400).json({
      success: false,
      errors: errors.array()
    });
  }

  next();
};
```

---

# Repository Layer

## repositories/complaint.repository.js

```javascript
class ComplaintRepository {

  async createComplaint(client, complaint) {

    const query = `
      INSERT INTO complaints
      (
        id,
        complaint_no,
        employee_id,
        subject,
        description,
        category,
        priority,
        status
      )
      VALUES
      ($1,$2,$3,$4,$5,$6,$7,$8)
      RETURNING *
    `;

    const values = [
      complaint.id,
      complaint.complaintNo,
      complaint.employeeId,
      complaint.subject,
      complaint.description,
      complaint.category,
      complaint.priority,
      complaint.status
    ];

    const result = await client.query(query, values);

    return result.rows[0];
  }

  async createAttachment(client, attachment) {

    const query = `
      INSERT INTO complaint_attachments
      (
        id,
        complaint_id,
        file_name,
        file_url,
        mime_type,
        file_size
      )
      VALUES ($1,$2,$3,$4,$5,$6)
    `;

    await client.query(query, [
      attachment.id,
      attachment.complaintId,
      attachment.fileName,
      attachment.fileUrl,
      attachment.mimeType,
      attachment.fileSize
    ]);
  }
}

module.exports = new ComplaintRepository();
```

---

# Service Layer

## services/complaint.service.js

```javascript
const { v4: uuid } = require("uuid");

const pool = require("../config/db");
const ApiError = require("../utils/ApiError");
const repository = require("../repositories/complaint.repository");

class ComplaintService {

  async createComplaint(payload, user) {

    const client = await pool.connect();

    try {

      await client.query("BEGIN");

      const complaint = {
        id: uuid(),
        complaintNo: `CMP-${Date.now()}`,
        employeeId: user.id,
        subject: payload.subject,
        description: payload.description,
        category: payload.category,
        priority: payload.priority || "MEDIUM",
        status: "OPEN"
      };

      const createdComplaint =
        await repository.createComplaint(client, complaint);

      if (payload.attachments?.length) {

        for (const file of payload.attachments) {

          await repository.createAttachment(client, {
            id: uuid(),
            complaintId: createdComplaint.id,
            fileName: file.fileName,
            fileUrl: file.fileUrl,
            mimeType: file.mimeType,
            fileSize: file.fileSize
          });
        }
      }

      await client.query("COMMIT");

      return createdComplaint;

    } catch (error) {

      await client.query("ROLLBACK");

      throw error;

    } finally {
      client.release();
    }
  }
}

module.exports = new ComplaintService();
```

---

# Controller Layer

## controllers/complaint.controller.js

```javascript
const complaintService =
  require("../services/complaint.service");

exports.createComplaint = async (req, res, next) => {

  try {

    const complaint =
      await complaintService.createComplaint(
        req.body,
        req.user
      );

    return res.status(201).json({
      success: true,
      message: "Complaint created successfully",
      data: complaint
    });

  } catch (error) {
    next(error);
  }
};
```

---

# Routes

## routes/complaint.routes.js

```javascript
const express = require("express");

const router = express.Router();

const auth = require("../middleware/auth.middleware");
const authorize =
  require("../middleware/authorize.middleware");

const validate =
  require("../middleware/validation.middleware");

const complaintController =
  require("../controllers/complaint.controller");

const {
  createComplaintValidation
} = require("../validations/complaint.validation");

router.post(
  "/",
  auth,
  authorize(
    "EMPLOYEE",
    "ADMIN"
  ),
  createComplaintValidation,
  validate,
  complaintController.createComplaint
);

module.exports = router;
```

---

# Error Handling Middleware

## middleware/error.middleware.js

```javascript
module.exports = (
  err,
  req,
  res,
  next
) => {

  console.error(err);

  const statusCode =
    err.statusCode || 500;

  res.status(statusCode).json({
    success: false,
    message:
      err.message ||
      "Internal Server Error"
  });
};
```

---

# Express App

## app.js

```javascript
const express = require("express");

const complaintRoutes =
  require("./routes/complaint.routes");

const errorMiddleware =
  require("./middleware/error.middleware");

const app = express();

app.use(express.json());

app.use("/api/v1/complaints",
  complaintRoutes
);

app.use(errorMiddleware);

module.exports = app;
```

---

# Server

## server.js

```javascript
const app = require("./app");
const env = require("./config/env");

app.listen(env.PORT, () => {
  console.log(
    `Server running on port ${env.PORT}`
  );
});
```

---

# JWT Payload Example

```json
{
  "id": "5fca3f0e-9719-4c4c-9b88-73d24ecf15d2",
  "email": "employee@company.com",
  "role": "EMPLOYEE"
}
```

---

# Create Complaint Request

### POST

```http
POST /api/v1/complaints
Authorization: Bearer <jwt>
```

Request Body

```json
{
  "subject": "Salary discrepancy",
  "description": "Salary credited is less than expected.",
  "category": "PAYROLL",
  "priority": "HIGH",
  "attachments": [
    {
      "fileName": "salary-slip.pdf",
      "fileUrl": "https://storage.company.com/docs/salary-slip.pdf",
      "mimeType": "application/pdf",
      "fileSize": 250000
    }
  ]
}
```

---

# Success Response

```json
{
  "success": true,
  "message": "Complaint created successfully",
  "data": {
    "id": "a2a58df9-5eb7-4af7-bd1f-f76dcb71fd44",
    "complaint_no": "CMP-1718899442000",
    "employee_id": "5fca3f0e-9719-4c4c-9b88-73d24ecf15d2",
    "subject": "Salary discrepancy",
    "description": "Salary credited is less than expected.",
    "category": "PAYROLL",
    "priority": "HIGH",
    "status": "OPEN"
  }
}
```

---

# Production Enhancements Recommended

1. Use database enums for roles, status, and priority.
2. Generate complaint numbers via PostgreSQL sequence.
3. Add audit trail table (`complaint_history`).
4. Add attachment virus scanning workflow.
5. Implement structured logging using `pino`.
6. Add rate limiting.
7. Add OpenAPI/Swagger documentation.
8. Use migration tools such as `node-pg-migrate` or `sequelize-cli`.
9. Implement optimistic locking/versioning.
10. Add complaint assignment workflow for GRO and Department Heads.
11. Add pagination and filtering endpoints.
12. Add integration tests using Jest + Supertest.

This design satisfies all stated requirements: layered architecture, JWT authentication, RBAC, validation, parameterized PostgreSQL queries, attachment metadata storage, transaction management, proper HTTP status codes, and centralized error handling.
