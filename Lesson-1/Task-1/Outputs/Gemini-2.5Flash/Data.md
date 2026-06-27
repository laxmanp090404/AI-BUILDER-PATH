# GEMINI 2.5 FLASH DATA
Here are the optimized PostgreSQL queries, indexing strategies, and architectural optimization decisions based on your schema.

---

## 📊 Optimized PostgreSQL Queries

### 1. Top 5 Departments with Highest Complaint Volume

To aggregate at the department level, we bridge `complaints` to `employees` via the reporter (`raised_by_employee_id`).

```sql
SELECT 
    e.department_id,
    COUNT(c.complaint_id) AS total_complaints
FROM complaints c
JOIN employees e ON c.raised_by_employee_id = e.employee_id
GROUP BY e.department_id
ORDER BY total_complaints DESC
LIMIT 5;

```

### 2. Average Resolution Time per Category

Using an explicit check for completed complaints (`resolved_at IS NOT NULL`) avoids calculating un-resolved data points.

```sql
SELECT 
    cat.category_id,
    cat.category_name,
    ROUND(AVG(EXTRACT(EPOCH FROM (c.resolved_at - c.created_at)) / 3600)::numeric, 2) AS avg_resolution_time_hours
FROM complaints c
JOIN categories cat ON c.category_id = cat.category_id
WHERE c.resolved_at IS NOT NULL
GROUP BY cat.category_id, cat.category_name;

```

### 3. SLA Breach Percentage per Department

This query uses the modern PostgreSQL `FILTER` clause. It allows us to calculate total numbers and targeted conditions simultaneously in a single scan, avoiding heavy conditional subqueries.

```sql
SELECT 
    cat.department_id,
    COUNT(c.complaint_id) AS total_complaints,
    COUNT(c.complaint_id) FILTER (
        WHERE c.resolved_at IS NOT NULL 
        AND (EXTRACT(EPOCH FROM (c.resolved_at - c.created_at)) / 3600) > cat.sla_hours
    ) AS breached_complaints,
    ROUND(
        (COUNT(c.complaint_id) FILTER (
            WHERE c.resolved_at IS NOT NULL 
            AND (EXTRACT(EPOCH FROM (c.resolved_at - c.created_at)) / 3600) > cat.sla_hours
        ) * 100.0) / COUNT(c.complaint_id), 2
    ) AS breach_percentage
FROM complaints c
JOIN categories cat ON c.category_id = cat.category_id
GROUP BY cat.department_id;

```

### 4. Escalated Complaints Count by Month

Using `DATE_TRUNC` creates standardized monthly buckets. This facilitates seamless reporting over time-series intervals.

```sql
SELECT 
    DATE_TRUNC('month', c.created_at) AS escalation_month,
    COUNT(c.complaint_id) AS escalated_count
FROM complaints c
WHERE c.escalation_level > 0
GROUP BY DATE_TRUNC('month', c.created_at)
ORDER BY escalation_month DESC;

```

### 5. Employee with Highest Complaints Assigned

This returns the individual worker currently possessing the highest volume of open/active payloads.

```sql
SELECT 
    e.employee_id,
    e.employee_name,
    COUNT(c.complaint_id) AS assigned_complaints_count
FROM complaints c
JOIN employees e ON c.current_owner_employee_id = e.employee_id
-- Optional filter: WHERE c.status_id != [RESOLVED_STATUS_ID] 
GROUP BY e.employee_id, e.employee_name
ORDER BY assigned_complaints_count DESC
LIMIT 1;

```

---

## ⚡ Indexing Strategy for High Performance

To ensure these queries run efficiently as the database scales, apply the following indexes:

```sql
-- For Query 1 & Query 5 (Optimizes Join and Foreign Key lookups)
CREATE INDEX idx_complaints_raised_by ON complaints(raised_by_employee_id);
CREATE INDEX idx_complaints_current_owner ON complaints(current_owner_employee_id);

-- For Query 2 & Query 3 (Partial index for resolution stats, filtering out open tickets)
CREATE INDEX idx_complaints_resolved_perf ON complaints(category_id, created_at, resolved_at) 
WHERE resolved_at IS NOT NULL;

-- For Query 4 (Speeds up time-series aggregations on escalations)
CREATE INDEX idx_complaints_escalation_tracker ON complaints(escalation_level, created_at) 
WHERE escalation_level > 0;

```

---

## 🧠 Query Optimization Decisions

* **The Power of `FILTER` over `CASE WHEN**`: In Query 3, using `FILTER (WHERE ...)` is much cleaner and more performant than older `SUM(CASE WHEN...)` structures. It provides the optimizer with clear statistics on filtered rows, leading to better execution plans.
* **Partial Indexes for Performance**: Instead of indexing every row's timestamps, the index `idx_complaints_resolved_perf` uses a `WHERE resolved_at IS NOT NULL` clause. This keeps the index small and fast by excluding active, unresolved tickets.
* **Epoch Arithmetic**: Using `EXTRACT(EPOCH FROM...)` converts intervals into seconds. Dividing by `3600` is a precise way to get fractional hours, allowing for accurate comparisons with the `sla_hours` column.
* **Foreign Key Optimization**: Adding indexes to `raised_by_employee_id` and `current_owner_employee_id` prevents slow, full-table scans during heavy `JOIN` and `GROUP BY` operations.