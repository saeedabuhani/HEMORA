# HEMORA

**Understanding change. Protecting health.**

HEMORA היא מערכת Full‑Stack בעברית וב־RTL לניהול, ניתוח, השוואה ומעקב אחר בדיקות דם. זהו אב־טיפוס לימודי של Clinical Decision Support: המנוע אינו מאבחן, אינו מנבא מחלה ואינו מחליף איש מקצוע רפואי.

## הפעלה מהירה עם Docker

```bash
cp .env.example .env
docker compose up --build
```

הממשק: `http://localhost:5173` · API: `http://localhost:8000` · OpenAPI: `http://localhost:8000/docs`

יש להחליף את כל הסודות בקובץ `.env` לפני סביבה שאינה מקומית. ליצירת מפתח הצפנה: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

## הפעלה ללא Docker

נדרש Python 3.12+, Node.js 20+ ו־PostgreSQL 16+.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

בחלון נוסף:

```bash
cd frontend
npm install
npm run dev
```

ברירת המחדל ללא `DATABASE_URL` היא SQLite מקומי לצורכי פיתוח בלבד. Docker משתמש ב־PostgreSQL.

## חשבונות הדגמה

| תפקיד | דוא״ל | סיסמה |
|---|---|---|
| מנהל | `admin@hemora.local` | `Hemora123!` |
| קלינאי | `clinician@hemora.local` | `Hemora123!` |
| מעבדה | `lab@hemora.local` | `Hemora123!` |
| מטופל | `patient@hemora.local` | `Hemora123!` |

החשבונות והסיסמאות מיועדים לפיתוח ולהדגמה בלבד. כל ששת המטופלים בדויים ומסומנים `DEMO DATA`.

## מבנה

```text
hemora/
├── backend/       FastAPI, SQLAlchemy, Alembic, pytest
├── frontend/      React, TypeScript, Vite, Tailwind, Vitest, Playwright
├── docs/          תיעוד הגשה, אבטחה, ארכיטקטורה ותסריט הצגה
├── sample-data/   קבצי CSV לתרחישי ההדגמה
├── docker-compose.yml
├── .env.example
├── SECURITY.md
└── LICENSE
```

## מנועים מרכזיים

- `ClinicalAnalysisEngine` מסווג NORMAL / LOW / HIGH / CRITICAL / UNKNOWN / UNVERIFIED מול טווח מתאים ושומר `HEMORA-CLINICAL-1.0.0`.
- `ReferenceRangeService` נותן קדימות לטווח המעבדה, אחריו הגדרת מעבדה ורק אז טווח הדגמה מסומן.
- `UnitConversionService` משווה יחידות רק לאחר המרה דטרמיניסטית מאושרת; אחרת מחזיר `NOT_COMPARABLE`.
- `TestComparisonEngine` מחשב שינוי, מעבר טווח ואמינות לפי התקרבות לטווח—לא לפי עלייה או ירידה בלבד.
- `LongitudinalTrendService` מסכם רצפים משלוש בדיקות ומעלה בלי לחזות מחלה.
- `PanelCompletenessService` מבדיל בין חסר לחריג.
- `RecommendationEngine` מפיק המלצות כלליות מבוססות כללים בלבד.

## אבטחה

Argon2, access/refresh JWT, RBAC בצד השרת, CORS מוגבל, כותרות אבטחה, ORM פרמטרי, הצפנת תעודת זהות, HMAC דטרמיניסטי לחיפוש ומניעת כפילות, הסתרה בממשק ו־Audit מסונן. אין לשמור סודות במאגר.

## Migration ונתוני הדגמה

```bash
cd backend
alembic upgrade head
python -m app.seed
```

פקודת ה־seed היא idempotent ויוצרת קטלוג מדדים, aliases, טווחי הדגמה, מעבדה, משתמשים, שישה מטופלים ותרחישי בדיקות.

## בדיקות ואימות

```bash
cd backend && pytest
cd frontend && npm test
cd frontend && npm run build
cd frontend && npx playwright install chromium && npm run e2e
docker compose config
```

תרחישי E2E מלאים דורשים backend עם seed פעיל. בדיקות PDF דורשות גופן Arial ב־Windows או DejaVu ב־Docker/Linux.

## API

ה־API כולל אימות, מטופלים, בדיקות, תוצאות, ניתוח, השוואה, מגמות, ייבוא, קטלוג מדדים, Audit ודוחות PDF/CSV. תיעוד אינטראקטיבי נמצא ב־`/docs`.

## תיעוד הגשה

ראו את `docs/PROJECT_OVERVIEW_HE.md`, `ARCHITECTURE_HE.md`, `DATABASE_DESIGN_HE.md`, `CLINICAL_LOGIC_HE.md`, `SECURITY_HE.md`, `TEST_PLAN_HE.md`, `USER_GUIDE_HE.md` ו־`PRESENTATION_SCRIPT_HE.md`.

## מגבלות ועבודה עתידית

זהו אב־טיפוס לימודי ולא מכשיר רפואי מאושר. לפני שימוש עם מידע אמיתי נדרשים אימות קליני ורגולטורי, מערכת ניהול מפתחות, MFA, מנגנון ביטול refresh tokens, הגבלת קצב מבוזרת, אחסון קבצים מאובטח, ניטור, גיבוי, התאוששות, בדיקות חדירה ותהליך איכות רפואי מלא. ייבוא PDF אינו מיושם, משום שאסור לשמור חילוץ לא מאומת; CSV מיושם עם Preview ואישור מפורש.

## הצהרה רפואית

HEMORA היא מערכת תומכת מידע ואינה מהווה אבחנה רפואית, ייעוץ רפואי או תחליף לבדיקה ולהחלטה של איש מקצוע רפואי. טווחי ייחוס עשויים להשתנות בין מעבדות ובין מטופלים.
