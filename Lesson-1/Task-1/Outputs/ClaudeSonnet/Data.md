## CLAUDE SONNET 4.6 -  Data

# Optimized PostgreSQL Queries

## Indexes (create these first)

```sql
-- Foreign key / join columns
CREATE INDEX idx_complaints_category_id ON complaints(category_id);
CREATE INDEX idx_complaints_owner_emp_id ON complaints(current_owner_employee_id);
CREATE INDEX idx_complaints_raised_by ON complaints(raised_by_employee_id);
CREATE INDEX idx_categories_department_id ON categories(department_id);

-- Filter/aggregation columns
CREATE INDEX idx_complaints_status_id ON complaints(status_id);
CREATE INDEX idx_complaints_escalation_level ON complaints(escalation_level) WHERE escalation_level > 0;
CREATE INDEX idx_complaints_created_at ON complaints(created_at);
CREATE INDEX idx_complaints_resolved_at ON complaints(resolved_at) WHERE resolved_at IS NOT NULL;

-- Composite index for SLA breach calc (covers join + filter + resolved check)
CREATE INDEX idx_complaints_cat_resolved ON complaints(category_id, resolved_at, created_at);

-- Composite for month-wise escalation reporting
CREATE INDEX idx_complaints_escalation_created ON complaints(escalation_level, created_at) WHERE escalation_level > 0;

-- Covering index for employee complaint counts
CREATE INDEX idx_complaints_owner_covering ON complaints(current_owner_employee_id) INCLUDE (complaint_id);
```

---

## 1. Top 5 Departments by Complaint Volume

```sql
SELECT
    e.department_id,
    COUNT(*) AS complaint_count
FROM complaints c
JOIN employees e ON e.employee_id = c.raised_by_employee_id
GROUP BY e.department_id
ORDER BY complaint_count DESC
LIMIT 5;
```

**Optimization notes:**
- Joins on `employees.employee_id` (PK, already indexed) — driving table is `complaints`, so an index on `raised_by_employee_id` is used for the join (already created above, or rely on FK index if present).
- `GROUP BY` + `LIMIT 5` lets the planner use a **top-N heap sort** instead of sorting the entire result set.
- If complaint volume is consistently tied to `category → department` rather than `raised_by` employee's department, confirm which department definition is correct (employee's own dept vs. category's dept — see query 3 for the alternate join path). Adjust join accordingly.

---

## 2. Average Resolution Time per Category

```sql
SELECT
    cat.category_id,
    cat.category_name,
    ROUND(AVG(EXTRACT(EPOCH FROM (c.resolved_at - c.created_at)) / 3600)::numeric, 2) AS avg_resolution_hours,
    COUNT(*) AS resolved_complaints
FROM complaints c
JOIN categories cat ON cat.category_id = c.category_id
WHERE c.resolved_at IS NOT NULL
GROUP BY cat.category_id, cat.category_name
ORDER BY avg_resolution_hours DESC;
```

**Optimization notes:**
- `WHERE resolved_at IS NOT NULL` filters before aggregation — paired with the partial index `idx_complaints_resolved_at`, this avoids scanning unresolved rows.
- `EXTRACT(EPOCH ...)` is computed in numeric seconds, cheaper than interval arithmetic in aggregate context.
- Aggregating on `categories.category_id` (PK) avoids extra lookups since `category_name` is functionally dependent.

---

## 3. SLA Breach Percentage per Department

```sql
SELECT
    cat.department_id,
    COUNT(*) FILTER (WHERE c.resolved_at IS NOT NULL) AS resolved_total,
    COUNT(*) FILTER (
        WHERE c.resolved_at IS NOT NULL
        AND c.resolved_at > c.created_at + (cat.sla_hours || ' hours')::interval
    ) AS breached_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.resolved_at IS NOT NULL
            AND c.resolved_at > c.created_at + (cat.sla_hours || ' hours')::interval
        ) / NULLIF(COUNT(*) FILTER (WHERE c.resolved_at IS NOT NULL), 0),
        2
    ) AS sla_breach_pct
FROM complaints c
JOIN categories cat ON cat.category_id = c.category_id
GROUP BY cat.department_id
ORDER BY sla_breach_pct DESC NULLS LAST;
```

**Optimization notes:**
- `FILTER` clauses let Postgres compute both numerator and denominator in a **single pass** over the joined rows instead of two separate subqueries/scans.
- `NULLIF` prevents divide-by-zero when a department has no resolved complaints.
- The composite index `idx_complaints_cat_resolved (category_id, resolved_at, created_at)` allows an **index-only-ish scan** for the join + filter + SLA comparison without hitting the heap for unrelated columns.
- Casting `sla_hours || ' hours'` is fine for moderate volume; for very high-frequency queries, consider pre-computing `created_at + sla_hours * interval '1 hour'` as a **generated column** on `complaints` (`sla_deadline`) and indexing it directly, e.g.:
```sql
ALTER TABLE complaints ADD COLUMN sla_deadline timestamptz
  GENERATED ALWAYS AS (created_at + (
    (SELECT sla_hours FROM categories WHERE categories.category_id = complaints.category_id) || ' hours'
  )::interval) STORED;
```
  (Note: Postgres generated columns can't reference other tables directly — in practice this is better handled via a trigger or materialized column populated on insert if you want it indexed.)

---

## 4. Escalated Complaints Count by Month

```sql
SELECT
    DATE_TRUNC('month', c.created_at) AS month,
    COUNT(*) AS escalated_count
FROM complaints c
WHERE c.escalation_level > 0
GROUP BY DATE_TRUNC('month', c.created_at)
ORDER BY month;
```

**Optimization notes:**
- The partial composite index `idx_complaints_escalation_created (escalation_level, created_at) WHERE escalation_level > 0` is tailor-made: it's small (only escalated rows), and supports both the filter and the grouping/sorting key.
- `DATE_TRUNC` in `GROUP BY` forces a computation per row; if this query runs frequently on large data, consider a **materialized view** refreshed nightly:
```sql
CREATE MATERIALIZED VIEW mv_escalations_by_month AS
SELECT DATE_TRUNC('month', created_at) AS month, COUNT(*) AS escalated_count
FROM complaints
WHERE escalation_level > 0
GROUP BY 1;
```

---

## 5. Employee with Highest Complaints Assigned

```sql
SELECT
    e.employee_id,
    e.employee_name,
    COUNT(*) AS assigned_complaints
FROM complaints c
JOIN employees e ON e.employee_id = c.current_owner_employee_id
GROUP BY e.employee_id, e.employee_name
ORDER BY assigned_complaints DESC
LIMIT 1;
```

**Optimization notes:**
- `idx_complaints_owner_emp_id` (or the covering version) lets Postgres aggregate via index scan rather than full table scan.
- `LIMIT 1` with `ORDER BY ... DESC` enables a top-N heapsort — much cheaper than sorting the full grouped result.
- If ties matter (multiple employees with the same max count), switch to a `RANK()` window function instead of `LIMIT 1`:
```sql
SELECT employee_id, employee_name, assigned_complaints
FROM (
    SELECT e.employee_id, e.employee_name, COUNT(*) AS assigned_complaints,
           RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
    FROM complaints c
    JOIN employees e ON e.employee_id = c.current_owner_employee_id
    GROUP BY e.employee_id, e.employee_name
) ranked
WHERE rnk = 1;
```

---

## General Optimization Principles Applied

| Decision | Reason |
|---|---|
| Indexes on all FK join columns | Avoids sequential scans / nested loop fallback to full table scans on joins |
| Partial indexes (`WHERE escalation_level > 0`, `resolved_at IS NOT NULL`) | Smaller index size, faster scans since most queries filter on these conditions anyway |
| Composite indexes ordered by filter-then-sort columns | Lets Postgres satisfy WHERE + GROUP BY/ORDER BY from index alone |
| `FILTER` clause instead of multiple `CASE WHEN` subqueries | Single table scan instead of multiple scans/joins |
| `LIMIT N` with `ORDER BY` | Enables top-N heapsort optimization (avoids full sort) |
| Avoiding `SELECT *` | Reduces I/O, enables index-only scans where possible |
| Materialized view suggestion for monthly aggregates | Amortizes computation cost for dashboard-style recurring queries |

---

**One clarifying point worth confirming:** for query 1, "department" could mean either the *complaint-raiser's* department (`employees.department_id`) or the *category's* department (`categories.department_id`) — these may differ if an employee in Dept A raises a complaint in a category owned by Dept B. I used the raiser's department; let me know if you want it switched to the category's department instead, and I'll adjust the query and index accordingly.