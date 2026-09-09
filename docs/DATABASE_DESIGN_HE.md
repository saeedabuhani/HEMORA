# עיצוב מסד הנתונים — HEMORA

## דיאגרמת ER

```mermaid
erDiagram
    CLINICS ||--o{ PATIENTS : "משייכת"
    CLINICS ||--o{ USERS : "מעסיקה"
    USERS ||--o{ DOCTOR_PATIENTS : "רופא מטפל ב"
    PATIENTS ||--o{ DOCTOR_PATIENTS : "מטופל על ידי"
    USERS ||--o| PATIENTS : "חשבון אישי של"
    PATIENTS ||--o{ BLOOD_TESTS : "עבר"
    LABORATORIES ||--o{ BLOOD_TESTS : "ביצעה"
    BLOOD_TESTS ||--o{ TEST_RESULTS : "מכילה"
    ANALYTES ||--o{ TEST_RESULTS : "מודד"
    ANALYTES ||--o{ ANALYTE_ALIASES : "שמות נרדפים"
    ANALYTES ||--o{ REFERENCE_RANGES : "טווחי ייחוס"
    ANALYTES ||--o{ CRITICAL_THRESHOLDS : "ספים קריטיים"
    LABORATORIES ||--o{ REFERENCE_RANGES : "טווח ספציפי"
    BLOOD_TESTS ||--o{ ANALYSIS_RUNS : "נותחה ב"
    ANALYSIS_RUNS ||--o{ ANALYSIS_FINDINGS : "מייצרת"
    PATIENTS ||--o{ ALERTS : "התראות"
    USERS ||--o{ AUDIT_LOGS : "מבצע"

    CLINICS {
        int id PK
        string name
        string code UK
        string city
        bool active
    }
    USERS {
        int id PK
        string email UK
        string password_hash
        enum role "ADMIN|DOCTOR|CLINIC|PATIENT"
        int clinic_id FK
        string patient_id FK
        bool is_active
    }
    DOCTOR_PATIENTS {
        int id PK
        int doctor_user_id FK
        string patient_id FK
        datetime assigned_at
        int assigned_by FK
    }
    PATIENTS {
        string id PK "UUID"
        string first_name
        string last_name
        string national_id_encrypted
        string national_id_hash UK
        date date_of_birth
        string biological_sex
        int clinic_id FK
        bool demo
    }
    BLOOD_TESTS {
        string id PK "UUID"
        string patient_id FK
        int laboratory_id FK
        date test_date
        string accession_number UK
        string panel
        bool fasting
        int created_by FK
    }
    TEST_RESULTS {
        int id PK
        string blood_test_id FK
        int analyte_id FK
        float numeric_value
        string unit
        float reference_min
        float reference_max
        float normalized_value
        string normalized_unit
        enum status
        enum data_quality_status
        string reference_source
    }
    ANALYTES {
        int id PK
        string code UK
        string display_name_he
        string category
        string typical_unit
    }
    REFERENCE_RANGES {
        int id PK
        int analyte_id FK
        int laboratory_id FK "nullable"
        string sex
        int age_min
        int age_max
        float min_value
        float max_value
        string source_reference
    }
    ANALYSIS_RUNS {
        int id PK
        string blood_test_id FK
        string algorithm_version
        json summary
        float quality_score
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string entity_type
        json metadata_sanitized
    }
```

## שלוש הטבלאות שמייצרות את מודל ההרשאות

| טבלה | תפקיד |
|---|---|
| `clinics` | ישות המרפאה |
| `patients.clinic_id` | כל מטופל שייך למרפאה אחת — הבסיס להרשאת CLINIC |
| `doctor_patients` | שיוך רבים־לרבים בין רופא למטופל — הבסיס להרשאת DOCTOR |

`doctor_patients` הוא רבים־לרבים בכוונה: למטופל אחד יכולים להיות כמה רופאים
מטפלים, ולרופא אחד יש הרבה מטופלים. יש `UniqueConstraint` על הצמד
`(doctor_user_id, patient_id)` כדי למנוע שיוך כפול.

## החלטות עיצוב

**תעודת זהות נשמרת פעמיים.**
`national_id_encrypted` מוצפן ב-Fernet וניתן לפענוח כדי להציג את הספרות
האחרונות; `national_id_hash` הוא HMAC-SHA256 דטרמיניסטי, מאונדקס וייחודי,
ומשמש לחיפוש ולמניעת כפילויות — בלי לחשוף את הערך. כך אפשר לאתר מטופל לפי
ת״ז מבלי לפענח אף רשומה.

**ערך גולמי וערך מנורמל נשמרים בנפרד.**
`numeric_value` + `unit` הם מה שהמעבדה שלחה, ולעולם לא משתנים.
`normalized_value` + `normalized_unit` הם התוצאה של המרה דטרמיניסטית מאושרת.
השוואות בין בדיקות משתמשות במנורמל; אם אין המרה בטוחה, המערכת מסמנת
`NOT_COMPARABLE` במקום להשוות.

**מקור טווח הייחוס נשמר בשדה.**
`reference_source` מקבל אחד מ-`LAB_SUPPLIED` / `LAB_CONFIG` / `DEMO_GENERAL` / `NONE`,
לפי סדר עדיפויות. כשמוצג טווח `DEMO_GENERAL`, הממשק חייב להציג הודעה
שהטווח כללי ושיש להעדיף את טווח המעבדה.

**ספים קריטיים בטבלה נפרדת.**
`critical_thresholds` נפרדת מ-`reference_ranges` כדי שלא ייווצר סף קריטי
בטעות מטווח ייחוס רגיל. סף נחשב תקף רק אם קיים בו `source_reference` מלא.

**ניתוח נשמר עם גרסה.**
כל `analysis_runs` שומר `algorithm_version`. שינוי עתידי בכללים לא יסתיר
את הבסיס שלפיו ניתנה תוצאה קודמת.

**Audit מסונן בכתיבה.**
`AuditService.record` מסיר מפתחות רגישים (`password`, `token`, `national_id`,
`medical_record`) לפני השמירה — הסינון קורה בשכבת השירות, לא בתצוגה.

## אינדקסים ואילוצים מרכזיים

| אילוץ | מטרה |
|---|---|
| `patients.national_id_hash` UNIQUE | מניעת מטופל כפול |
| `blood_tests.accession_number` UNIQUE | מניעת קליטה כפולה של אותה בדיקה |
| `test_results (blood_test_id, analyte_id)` UNIQUE | מדד לא יופיע פעמיים באותה בדיקה |
| `doctor_patients (doctor_user_id, patient_id)` UNIQUE | מניעת שיוך כפול |
| `analyte_aliases.alias` UNIQUE | מיפוי חד־ערכי בייבוא |
| `ix_results_test_status` | סינון מהיר של תוצאות חריגות |
| אינדקסים על `patients.clinic_id`, `doctor_patients.*` | שאילתות ההרשאות |

## Migrations

הסכימה מנוהלת ב-Alembic (`backend/alembic/`).

```bash
cd backend
alembic upgrade head
python -m app.seed
```

פקודת ה-seed היא idempotent — אם כבר קיימים משתמשים היא יוצאת מיד.
כדי לבנות מחדש נתוני הדגמה: מחקו את `backend/hemora.db` והריצו שוב.
