# תכנון מסד הנתונים

```mermaid
erDiagram
  USERS ||--o| PATIENTS : linked_profile
  PATIENTS ||--o{ BLOOD_TESTS : has
  LABORATORIES ||--o{ BLOOD_TESTS : performs
  BLOOD_TESTS ||--o{ TEST_RESULTS : contains
  ANALYTES ||--o{ TEST_RESULTS : describes
  ANALYTES ||--o{ REFERENCE_RANGES : configures
  ANALYTES ||--o{ CRITICAL_THRESHOLDS : validates
  BLOOD_TESTS ||--o{ ANALYSIS_RUNS : analyzed_by
  ANALYSIS_RUNS ||--o{ ANALYSIS_FINDINGS : produces
  USERS ||--o{ AUDIT_LOGS : creates
```

המזהים הרפואיים הם UUID. תעודת זהות נשמרת מוצפנת ולצידה HMAC דטרמיניסטי לחיפוש וייחודיות. מפתחות זרים, אילוצי ייחודיות ואינדקסים מגנים על עקביות וביצועים. כל הזמנים נשמרים UTC.
