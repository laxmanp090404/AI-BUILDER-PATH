# GEMINI 2.5 FLASH APPDEV
As a senior backend engineer, I will design this Complaint & Grievance Redressal system using a clean, layered architecture (**Controller-Service-Repository pattern**). This separates transport, business logic, and data access layers, ensuring the system is maintainable, testable, and production-ready.

Here is the complete production-quality design and implementation.

---

## 📂 Project Structure

```text
grievance-redressal-api/
├── src/
│   ├── config/
│   │   └── db.js            # PostgreSQL pool configuration
│   ├── middlewares/
│   │   ├── auth.middleware.js # JWT & Role validation
│   │   └── error.middleware.js# Centralized error handler
│   ├── controllers/
│   │   └── complaint.controller.js
│   ├── services/
│   │   └── complaint.service.js
│   ├── repositories/
│   │   └── complaint.repository.js
│   ├── utils/
│   │   └── app-error.js      # Custom operational error class
│   └── app.js                # Express app setup & routing
├── package.json
└── server.js                 # App entry point

```

---

## 🛠️ Implementation

### 1. Database Schema & Pool Configuration

First, ensure your PostgreSQL database has the required tables.

```sql
CREATE TYPE user_role AS ENUM ('EMPLOYEE', 'GRO', 'DEPARTMENT_HEAD', 'ADMIN');
CREATE TYPE complaint_status AS ENUM ('PENDING', 'ASSIGNED', 'RESOLVED', 'REJECTED');

CREATE TABLE complaints (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    department_id INT NOT NULL,
    status complaint_status DEFAULT 'PENDING',
    created_by INT NOT NULL, -- References users table
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE complaint_attachments (
    id SERIAL PRIMARY KEY,
    complaint_id INT REFERENCES complaints(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(512) NOT NULL,
    file_size INT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

```

#### `src/config/db.js`

```javascript
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20, // Production pool sizing
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

module.exports = {
  query: (text, params) => pool.query(text, params),
  getTransaction: async () => {
    const client = await pool.connect();
    const query = client.query.bind(client);
    const release = client.release.bind(client);
    return { client, query, release };
  }
};

```

---

### 2. Custom Error & Centralized Error Middleware

#### `src/utils/app-error.js`

```javascript
class AppError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true; // Differentiates operational bugs from system programming errors
    Error.captureStackTrace(this, this.constructor);
  }
}

module.exports = AppError;

```

#### `src/middlewares/error.middleware.js`

```javascript
module.exports = (err, req, res, next) => {
  err.statusCode = err.statusCode || 500;
  err.status = err.status || 'error';

  if (process.env.NODE_ENV === 'development') {
    return res.status(err.statusCode).json({
      status: err.status,
      error: err,
      message: err.message,
      stack: err.stack
    });
  }

  // Production Error Response
  if (err.isOperational) {
    return res.status(err.statusCode).json({
      status: 'fail',
      message: err.message
    });
  }

  // Log unhandled programming errors securely
  console.error('ERROR 💥:', err);
  return res.status(500).json({
    status: 'error',
    message: 'Something went radically wrong!'
  });
};

```

---

### 3. Authentication & RBAC Middleware

#### `src/middlewares/auth.middleware.js`

```javascript
const jwt = require('jsonwebtoken');
const AppError = require('../utils/app-error');

exports.protect = (req, res, next) => {
  let token;
  if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
    token = req.headers.authorization.split(' ')[1];
  }

  if (!token) {
    return next(new AppError('You are not logged in. Please provide a valid token.', 401));
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    // Expecting payload structure: { id: 1, role: 'EMPLOYEE' }
    req.user = decoded; 
    next();
  } catch (error) {
    return next(new AppError('Invalid or expired token.', 401));
  }
};

exports.restrictTo = (...roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return next(new AppError('You do not have permission to perform this action.', 403));
    }
    next();
  };
};

```

---

### 4. Layered Architecture Components

#### `src/repositories/complaint.repository.js`

```javascript
const db = require('../config/db');

class ComplaintRepository {
  async createComplaintWithAttachments(complaintData, attachments, client = null) {
    // If a transaction client is passed, use it; otherwise fallback to standard pool query
    const queryExecutor = client ? client.query.bind(client) : db.query.bind(db);

    // 1. Insert Complaint
    const complaintQuery = `
      INSERT INTO complaints (title, description, department_id, created_by)
      VALUES ($1, $2, $3, $4)
      RETURNING id, title, description, department_id, status, created_at;
    `;
    const complaintValues = [
      complaintData.title,
      complaintData.description,
      complaintData.departmentId,
      complaintData.userId
    ];
    
    const { rows } = await queryExecutor(complaintQuery, complaintValues);
    const complaint = rows[0];

    // 2. Insert Attachments bulk style if present
    if (attachments && attachments.length > 0) {
      complaint.attachments = [];
      for (const file of attachments) {
        const attachmentQuery = `
          INSERT INTO complaint_attachments (complaint_id, file_name, file_url, file_size)
          VALUES ($1, $2, $3, $4)
          RETURNING id, file_name, file_url;
        `;
        const attachmentValues = [complaint.id, file.name, file.url, file.size];
        const attachmentResult = await queryExecutor(attachmentQuery, attachmentValues);
        complaint.attachments.push(attachmentResult.rows[0]);
      }
    }

    return complaint;
  }
}

module.exports = new ComplaintRepository();

```

#### `src/services/complaint.service.js`

```javascript
const complaintRepository = require('../repositories/complaint.repository');
const db = require('../config/db');
const AppError = require('../utils/app-error');

class ComplaintService {
  async fileNewComplaint(complaintData, attachments) {
    // Basic Joi-like validation fallback logic
    if (!complaintData.title || !complaintData.description || !complaintData.departmentId) {
      throw new AppError('Title, description, and departmentId are required fields.', 400);
    }

    // Explicitly managing an ACID transaction block for multi-table insertion
    const tx = await db.getTransaction();
    
    try {
      await tx.client.query('BEGIN');

      const complaint = await complaintRepository.createComplaintWithAttachments(
        complaintData, 
        attachments, 
        tx.client
      );

      await tx.client.query('COMMIT');
      return complaint;
    } catch (error) {
      await tx.client.query('ROLLBACK');
      throw error; // Let the centralized controller pass it to error middleware
    } finally {
      tx.release();
    }
  }
}

module.exports = new ComplaintService();

```

#### `src/controllers/complaint.controller.js`

```javascript
const complaintService = require('../services/complaint.service');

exports.createComplaint = async (req, res, next) => {
  try {
    const complaintData = {
      title: req.body.title,
      description: req.body.description,
      departmentId: req.body.departmentId,
      userId: req.user.id // Injected from `protect` middleware
    };

    // Expecting array structure from file upload middleware (e.g., multer)
    const attachments = req.body.attachments || []; 

    const newComplaint = await complaintService.fileNewComplaint(complaintData, attachments);

    return res.status(201).json({
      status: 'success',
      data: {
        complaint: newComplaint
      }
    });
  } catch (error) {
    next(error);
  }
};

```

---

### 5. Application Orchestration & Entry Point

#### `src/app.js`

```javascript
const express = require('express');
const { protect, restrictTo } = require('./middlewares/auth.middleware');
const complaintController = require('./controllers/complaint.controller');
const globalErrorHandler = require('./middlewares/error.middleware');
const AppError = require('./utils/app-error');

const app = express();

app.use(express.json());

// Complaint Routing
// Only authorized roles (e.g., EMPLOYEE) can generate complaints. 
// GRO, DEPARTMENT_HEAD, ADMIN can easily be added to access it if required.
app.post(
  '/api/v1/complaints',
  protect,
  restrictTo('EMPLOYEE'), 
  complaintController.createComplaint
);

// Fallback Route
app.all('*', (req, res, next) => {
  next(new AppError(`Can't find ${req.originalUrl} on this server!`, 404));
});

// Centralized Global Error Handler Middleware
app.use(globalErrorHandler);

module.exports = app;

```

#### `server.js`

```javascript
require('dotenv').config();
const app = require('./src/app');

const PORT = process.env.PORT || 3000;

const server = app.listen(PORT, () => {
  console.log(`Application context serving live on port ${PORT}...`);
});

// Unhandled Rejections protection safety net
process.on('unhandledRejection', (err) => {
  console.error('UNHANDLED REJECTION! 💥 Shutting down gracefully...');
  console.error(err.name, err.message);
  server.close(() => {
    process.exit(1);
  });
});

```

---

## 🛡️ Production Design Choices Highlighted

* **Explicit Transaction Safety:** The `complaint.service.js` isolates transaction blocks natively (`BEGIN`, `COMMIT`, `ROLLBACK`) ensuring if the file attachment execution block drops half-way through, data integrity remains pure.
* **Parameterized SQL Core:** Strict prevention against SQL Injections by assigning runtime variables securely wrapped inside `$1, $2, ...` query sequences inside the repository module.
* **Strict Security & RBAC:** Combined validation verifying individual JWT legitimacy paired with custom middleware arrays prioritizing native database enum mappings (`EMPLOYEE`, `GRO`, `DEPARTMENT_HEAD`, `ADMIN`).