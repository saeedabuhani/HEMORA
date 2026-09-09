# ארכיטקטורה — HEMORA

## תמונה כללית

```mermaid
flowchart TB
    Browser["דפדפן — עברית / RTL"]

    subgraph FE["Frontend · React + TypeScript + Vite"]
        Router["React Router"]
        Query["TanStack Query — cache"]
        UI["Tailwind · Recharts · Lucide"]
    end

    subgraph BE["Backend · FastAPI"]
        API["API Routes · /api"]
        Auth["Auth + RBAC<br/>scope_patients / assert_patient_access"]

        subgraph SVC["Service Layer"]
            PS["PatientService"]
            BS["BloodTestService"]
            UCS["UnitConversionService"]
            RRS["ReferenceRangeService"]
            CAE["ClinicalAnalysisEngine"]
            TCE["TestComparisonEngine"]
            LTS["LongitudinalTrendService"]
            PCS["PanelCompletenessService"]
            RE["RecommendationEngine"]
            EXP["ExplanationService"]
            RS["ReportService"]
            AS["AuditService"]
            IS["ImportService"]
        end
    end

    DB[("PostgreSQL / SQLite<br/>SQLAlchemy 2 + Alembic")]

    Browser --> FE
    FE -->|"JSON + JWT"| API
    API --> Auth
    Auth --> SVC
    SVC --> DB
```

## עקרונות

**הלוגיקה העסקית לא יושבת ב-routes.** ה-routes מבצעים אימות, הרשאה ותרגום שגיאות
בלבד; כל החישוב הקליני נמצא ב-`services.py`. כך אפשר לבדוק את המנועים ביחידה
בלי להרים שרת, וזה מה שמאפשר את 32 הבדיקות האוטומטיות.

**נקודת אכיפה אחת להרשאות.** במקום לשכפל תנאי `if role == ...` בכל endpoint,
יש שתי פונקציות ב-`backend/app/api.py`:

| פונקציה | תפקיד |
|---|---|
| `scope_patients(query, user)` | מוסיפה `WHERE` לכל שאילתה שמחזירה מטופלים |
| `assert_patient_access(db, user, patient_id)` | מחזירה את המטופל, או 403 / 404 |

כל endpoint שנוגע במטופל או בבדיקה עובר דרכן. אם בעתיד יתווסף תפקיד חמישי,
משנים מקום אחד.

**סדר הבדיקות חשוב.** ב-`create_test` ההרשאה נבדקת *לפני* אימות הקלט,
כדי שמשתמש בלי הרשאה לא יוכל ללמוד אם מספר בדיקה או מעבדה קיימים.

## זרימת בקשה — הוספת בדיקת דם

```mermaid
sequenceDiagram
    participant U as רופא
    participant FE as Frontend
    participant API as FastAPI
    participant SVC as Service Layer
    participant DB as Database

    U->>FE: מזין תוצאות
    FE->>API: POST /api/tests (JWT)
    API->>API: assert_patient_access — האם המטופל שלו?
    API->>DB: אימות מעבדה, מספר בדיקה, תאריך
    API->>SVC: ClinicalAnalysisEngine.analyze
    SVC->>SVC: ReferenceRangeService — פתרון טווח
    SVC->>SVC: UnitConversionService — נרמול יחידות
    SVC->>SVC: סיווג NORMAL / LOW / HIGH / CRITICAL
    SVC->>SVC: PanelCompletenessService — מה חסר
    SVC->>DB: AnalysisRun + Findings + Alerts
    SVC->>DB: AuditService — רישום פעולה
    API-->>FE: test_id + analysis_run_id
```

## זרימת הסבר — "למה HEMORA מציגה את זה?"

```mermaid
flowchart LR
    Click["לחיצה על 'למה?'"] --> EP["GET /tests/{id}/results/{rid}/explanation"]
    EP --> Guard["authorized_test — בדיקת הרשאה"]
    Guard --> ES["ExplanationService.build"]
    ES --> Prev["איתור התוצאה המקבילה<br/>בבדיקה הקודמת"]
    ES --> TCE["TestComparisonEngine<br/>לחישוב המגמה"]
    ES --> Out["הסבר מנוסח מהנתונים השמורים"]
```

ה-`ExplanationService` לא מחזיק טקסט קבוע לכל מדד. הוא מרכיב את המשפטים
מהערכים שנשמרו בפועל, ולכן ההסבר נשאר נכון גם אם הנתונים או הטווחים ישתנו.

## שכבות ותיקיות

```text
backend/app/
├── main.py         הרכבת האפליקציה, CORS, כותרות אבטחה, טיפול בשגיאות
├── api.py          routes + אכיפת הרשאות
├── management.py   routes לניהול (ADMIN) והתראות
├── services.py     כל המנועים הקליניים
├── reporting.py    יצירת PDF בעברית
├── models.py       טבלאות SQLAlchemy
├── schemas.py      אימות קלט/פלט (Pydantic v2)
├── security.py     Argon2, JWT, הצפנת ת״ז, בדיקת ספרת ביקורת
├── seed.py         נתוני הדגמה
└── database.py     engine + session

frontend/src/
├── App.tsx         מסכים ראשיים + ניווט לפי תפקיד
├── api.ts          שכבת גישה ל-API + ApiError
├── components.tsx  לוגו, StatusBadge, מצבי ריק/שגיאה
├── NewPatient.tsx  יצירת מטופל
├── NewTest.tsx     הזנת בדיקה ידנית
└── Management.tsx  ניהול קטלוג ומרכז התראות
```

## החלטות טכניות

| החלטה | נימוק |
|---|---|
| ניתוח דטרמיניסטי, לא LLM | חובה שיהיה ניתן להסביר ולשחזר כל סיווג קליני |
| גרסאות אלגוריתם (`HEMORA-CLINICAL-1.0.0`) | שינוי כללים בעתיד יישאר עקיב לאחור |
| נרמול יחידות לפני השוואה | השוואה בין יחידות שונות היא שגיאה קלינית |
| `doctor_patients` כרבים־לרבים | מטופל יכול להיות מטופל על ידי יותר מרופא אחד |
| SQLite כברירת מחדל | הרצה מקומית מיידית; docker-compose מריץ PostgreSQL |
| 4xx ללא retry ב-TanStack Query | 403 היא תשובה מכוונת — אין טעם לנסות שוב |
