# GPT-4o Data
Assumptions:

* `employees.department_id` identifies the employee's department.
* `categories.department_id` identifies the department responsible for that complaint category.
* A complaint is considered resolved when `resolved_at IS NOT NULL`.
* An SLA breach occurs when resolution time exceeds `categories.sla_hours`.
* PostgreSQL version supports `FILTER` clauses and modern query planner optimizations.

---

# 1. Top 5 Departments with Highest Complaint Volume

```sql
SELECT
    c.department_id,
    COUNT(*) AS complaint_count
FROM complaints comp
JOIN categories c
    ON c.category_id = comp.category_id
GROUP BY c.department_id
ORDER BY complaint_count DESC
LIMIT 5;
```

### Alternative (with department name table if available)

```sql
SELECT
    d.department_name,
    COUNT(*) AS complaint_count
FROM complaints comp
JOIN categories c
    ON c.category_id = comp.category_id
JOIN departments d
    ON d.department_id = c.department_id
GROUP BY d.department_name
ORDER BY complaint_count DESC
LIMIT 5;
```

---

# 2. Average Resolution Time per Category

### In Hours

```sql
SELECT
    c.category_id,
    c.category_name,
    ROUND(
        AVG(
            EXTRACT(EPOCH FROM (comp.resolved_at - comp.created_at))
        ) / 3600,
        2
    ) AS avg_resolution_hours
FROM complaints comp
JOIN categories c
    ON c.category_id = comp.category_id
WHERE comp.resolved_at IS NOT NULL
GROUP BY
    c.category_id,
    c.category_name
ORDER BY avg_resolution_hours DESC;
```

### Using PostgreSQL Interval

```sql
SELECT
    c.category_id,
    c.category_name,
    AVG(comp.resolved_at - comp.created_at) AS avg_resolution_time
FROM complaints comp
JOIN categories c
    ON c.category_id = comp.category_id
WHERE comp.resolved_at IS NOT NULL
GROUP BY c.category_id, c.category_name;
```

---

# 3. SLA Breach Percentage per Department

```sql
SELECT
    c.department_id,
    COUNT(*) AS total_resolved,
    COUNT(*) FILTER (
        WHERE
            EXTRACT(EPOCH FROM (comp.resolved_at - comp.created_at))
            > (c.sla_hours * 3600)
    ) AS breached_count,
    ROUND(
        100.0 *
        COUNT(*) FILTER (
            WHERE
                EXTRACT(EPOCH FROM (comp.resolved_at - comp.created_at))
                > (c.sla_hours * 3600)
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS breach_percentage
FROM complaints comp
JOIN categories c
    ON c.category_id = comp.category_id
WHERE comp.resolved_at IS NOT NULL
GROUP BY c.department_id
ORDER BY breach_percentage DESC;
```

---

# 4. Escalated Complaints Count by Month

### All escalated complaints

```sql
SELECT
    DATE_TRUNC('month', created_at) AS complaint_month,
    COUNT(*) AS escalated_complaints
FROM complaints
WHERE escalation_level > 0
GROUP BY complaint_month
ORDER BY complaint_month;
```

### By escalation level

```sql
SELECT
    DATE_TRUNC('month', created_at) AS complaint_month,
    escalation_level,
    COUNT(*) AS complaint_count
FROM complaints
WHERE escalation_level > 0
GROUP BY
    complaint_month,
    escalation_level
ORDER BY
    complaint_month,
    escalation_level;
```

---

# 5. Employee with Highest Complaints Assigned

### Top employee

```sql
SELECT
    e.employee_id,
    e.employee_name,
    COUNT(*) AS assigned_complaints
FROM complaints comp
JOIN employees e
    ON e.employee_id = comp.current_owner_employee_id
GROUP BY
    e.employee_id,
    e.employee_name
ORDER BY assigned_complaints DESC
LIMIT 1;
```

### Top N employees

```sql
SELECT
    e.employee_id,
    e.employee_name,
    COUNT(*) AS assigned_complaints
FROM complaints comp
JOIN employees e
    ON e.employee_id = comp.current_owner_employee_id
GROUP BY
    e.employee_id,
    e.employee_name
ORDER BY assigned_complaints DESC
LIMIT 10;
```

---

# Recommended Indexes

## complaints table

### Foreign-key joins

```sql
CREATE INDEX idx_complaints_category
    ON complaints(category_id);

CREATE INDEX idx_complaints_owner
    ON complaints(current_owner_employee_id);

CREATE INDEX idx_complaints_raised_by
    ON complaints(raised_by_employee_id);
```

### Resolution analytics

```sql
CREATE INDEX idx_complaints_resolved
    ON complaints(resolved_at)
    WHERE resolved_at IS NOT NULL;
```

### Time-series reporting

```sql
CREATE INDEX idx_complaints_created_at
    ON complaints(created_at);
```

### Escalation reporting

```sql
CREATE INDEX idx_complaints_escalation_created
    ON complaints(escalation_level, created_at)
    WHERE escalation_level > 0;
```

---

## categories table

```sql
CREATE INDEX idx_categories_department
    ON categories(department_id);
```

---

## employees table

```sql
CREATE INDEX idx_employees_department
    ON employees(department_id);
```

---

# Advanced Optimization (Large Tables)

If the complaints table contains tens or hundreds of millions of rows:

## Covering Index for Analytics

```sql
CREATE INDEX idx_complaints_analytics
ON complaints (
    category_id,
    created_at,
    resolved_at,
    escalation_level
);
```

This allows PostgreSQL to satisfy many analytical queries with fewer heap accesses.

---

## Monthly Partitioning

```sql
CREATE TABLE complaints (
    ...
) PARTITION BY RANGE (created_at);
```

Example partitions:

```sql
CREATE TABLE complaints_2026_01
PARTITION OF complaints
FOR VALUES FROM ('2026-01-01')
TO ('2026-02-01');

CREATE TABLE complaints_2026_02
PARTITION OF complaints
FOR VALUES FROM ('2026-02-01')
TO ('2026-03-01');
```

Benefits:

* Faster monthly reports.
* Partition pruning.
* Reduced index size.
* Easier archival.

---

# Why These Queries Are Efficient

1. **Aggregate after joining on indexed keys** (`category_id`, `employee_id`).
2. **Avoid correlated subqueries**, which cause repeated scans.
3. Use PostgreSQL's **FILTER** clause instead of multiple CASE expressions for cleaner aggregation.
4. Use **partial indexes** (`WHERE resolved_at IS NOT NULL`, `WHERE escalation_level > 0`) to reduce index size and improve selectivity.
5. Use **DATE_TRUNC()** for efficient time bucketing.
6. Support large-scale reporting through **partitioning** and **covering indexes**.
7. Keep joins on integer keys (`category_id`, `employee_id`, `department_id`) to maximize planner efficiency.

For very large datasets (100M+ complaints), the next optimization step would be creating **materialized views** that pre-aggregate complaint counts, SLA metrics, and monthly escalations, refreshing them periodically instead of scanning the raw table for every dashboard query.
