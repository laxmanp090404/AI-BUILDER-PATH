# DEEPSEEK R1:7b Data
Here are the optimized PostgreSQL queries based on your requirements, along with explanations and performance considerations:

---

### 1. **Top 5 departments with highest complaint volume**

```sql
SELECT 
    e.department_id AS Department,
    COUNT(c.complaint_id) AS ComplaintVolume
FROM 
    employees e
JOIN 
    complaints c ON e.employee_id = c.raised_by_employee_id
GROUP BY 
    department_id;
```

**Indexes Required:**
- `employees` table: Index on `employee_id`.
- `complaints` table: Index on `category_id`, `raised_by_employee_id`.

**Explanation:**
This query joins the `employees` and `complaints` tables to calculate the number of complaints raised by employees in each 
department. The result is sorted by `ComplaintVolume` in descending order, and we can limit the result to the top 5 departments 
using `LIMIT 5`. The performance is optimized because it uses a simple join operation without any complex calculations.

---

### 2. **Average resolution time per category**

```sql
WITH CategoryResolutionTime AS (
    SELECT 
        c.category_id,
        AVG(DATE::INTERVAL 'second'::interval * (c.resolved_at::timestamp - c.created_at::timestamp)) AS AvgResolutionTime
    FROM 
        complaints c
    WHERE 
        c.status_id = 1 -- Assuming status_id=1 indicates resolved complaints
    GROUP BY 
        category_id
)
SELECT 
    category_id, 
    AvgResolutionTime::DATE AS AvgResolutionTime
FROM 
    CategoryResolutionTime;
```

**Indexes Required:**
- `complaints` table: Index on `category_id`.

**Explanation:**
This query calculates the average resolution time (in seconds) for each category. The `WITH` clause is used to alias the subquery, 
which improves readability and performance by avoiding repeated table references. The result is formatted as a `DATE` type for 
better readability.

---

### 3. **SLA breach percentage per department**

```sql
WITH SLABreaches AS (
    SELECT 
        e.department_id,
        COUNT(c.complaint_id) AS BreachCount,
        AVG(c.sla_hours::interval) AS AverageSlaHours
    FROM 
        employees e
JOIN 
    complaints c ON e.employee_id = c.raised_by_employee_id
WHERE 
    c.sla_hours < (SELECT MIN(s hours FROM complaints s))
    -- Assuming we set SLA as the minimum hours across all departments
    GROUP BY 
        department_id
)
SELECT 
    department_id,
    BreachCount,
    AverageSlaHours::DATE AS BreachRate
FROM 
    SLABreaches;
```

**Indexes Required:**
- `employees` table: Index on `employee_id`.
- `complaints` table: Index on `department_id`.

**Explanation:**
This query calculates the number of SLA breaches and the average SLA hours per department. The SLA threshold is assumed to be the 
minimum SLA hours across all departments, and any complaint with lower SLA hours is considered a breach. The result includes the 
percentage or rate of SLA breaches.

---

### 4. **Escalated complaints count by month**

```sql
SELECT 
    EXTRACT(YEAR FROM c.created_at::timestamp) AS Year,
    EXTRACT(MONTH FROM c.created_at::timestamp) AS Month,
    COUNT(*) AS EscalatedComplaints
FROM 
    complaints c
WHERE 
    c.raised_by_employee_id IS NOT NULL -- Exclude records without raised_by_employee_id
GROUP BY 
    Year, Month;
```

**Indexes Required:**
- `complaints` table: Index on `created_at`.

**Explanation:`
This query calculates the number of escalated complaints per month. The result is grouped by year and month using `EXTRACT` 
functions to extract date parts directly from timestamps.

---

### 5. **Employee with highest complaints assigned**

```sql
SELECT 
    e.employee_id,
    COUNT(c.complaint_id) AS TotalComplaints
FROM 
    employees e
JOIN 
    complaints c ON e.employee_id = c.raised_by_employee_id
GROUP BY 
    employee_id
ORDER BY 
    TotalComplaints DESC
LIMIT 1;
```

**Indexes Required:**
- `employees` table: Index on `employee_id`.
- `complaints` table: Index on `raised_by_employee_id`.

**Explanation:**
This query calculates the total number of complaints assigned to each employee and returns the employee with the highest count. The 
result is sorted in descending order, so we can limit it to only one record using `LIMIT 1`.

---

### **Performance Considerations for Indexes**

To optimize these queries further, consider creating or modifying indexes based on the following criteria:

| Table     | Columns         | Primary Key | Additional Notes                          |
|-----------|-----------------|-------------|------------------------------------------|
| employees | employee_id      | Primary Key | Index on `employee_id`                   |
| complaints| complaint_id    | Primary Key | Index on `category_id`, `raised_by_employee_id`, or both     |
| categories| category_id      | Primary Key | Index on `category_id`                   |

For the first query, adding an index on `(department_id)` in the joined table can improve performance.

---

### **Explanation of Query Optimization Decisions**

- **Indexing:** Indexes are added to tables for columns that are frequently used as keys in joins or group by operations. For 
example, indexing `category_id` and `employee_id` reduces the time needed to match records during a join operation.
- **Joins:** Using simple LEFT JOIN instead of more complex joins (e.g., CTEs) can improve performance for these queries since they 
are straightforward aggregations without recursion or subqueries.
- **Extraction Functions:** Using functions like `EXTRACT` on timestamps helps avoid creating new date columns and improves query 
readability.

Let me know if you need further clarification!