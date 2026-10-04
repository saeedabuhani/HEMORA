# HEMORA

**Understanding change. Protecting health.**

HEMORA היא מערכת Full-Stack בעברית וב-RTL לניהול, ניתוח, השוואה ומעקב אחר בדיקות
דם לאורך זמן. זהו אב־טיפוס לימודי של Clinical Decision Support: המנוע אינו מאבחן,
אינו מנבא מחלה ואינו מחליף איש מקצוע רפואי.

---

## מה המערכת עושה

1. שומרת מטופלים והיסטוריית בדיקות דם
2. מסווגת כל תוצאה מול טווח הייחוס המתאים לה, ומציגה **מאיפה הטווח הגיע**
3. מסבירה כל מדד בעברית פשוטה
4. משווה כל בדיקה חדשה לקודמת — מדד מול מדד
5. מזהה שיפור, החמרה, יציבות, חריגה חדשה או חזרה לטווח
6. מבדילה בין **נתון חסר** לבין **נתון חריג**
7. מסבירה לכל ממצא בדיוק על מה הוא מבוסס
8. מפיקה דוח PDF בעברית

---

## הרשאות — ארבעה תפקידים

| תפקיד | רואה |
|---|---|
| **מנהל מערכת** | כל המטופלים, ניהול הקטלוג והמשתמשים, יומן ביקורת |
| **רופא** | רק את המטופלים המשויכים אליו |
| **מרפאה** | רק את המטופלים השייכים למרפאה שלה |
| **מטופל** | את התיק שלו בלבד |

ההפרדה נאכפת בשרת בשתי פונקציות מרכזיות ב-`backend/app/api.py` —
`scope_patients` ו-`assert_patient_access` — שכל endpoint הנוגע במטופל עובר דרכן.
הסתרת פריטים בממשק היא נוחות בלבד; ניסיון גישה ישיר דרך URL מוחזר עם 403.

---

## הפעלה מהירה עם Docker

```bash
cp .env.example .env
docker compose up --build
```

הממשק: `http://localhost:5173` · API: `http://localhost:8000` · OpenAPI: `http://localhost:8000/docs`

יש להחליף את כל הסודות ב-`.env` לפני סביבה שאינה מקומית.
ליצירת מפתח הצפנה:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## הפעלה ללא Docker

נדרשים Python 3.12+ ו-Node.js 20+.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
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

ברירת המחדל ללא `DATABASE_URL` היא SQLite מקומי לצורכי פיתוח בלבד.
Docker משתמש ב-PostgreSQL, עם אותו קוד בדיוק.

---

## חשבונות הדגמה

**הסיסמה זהה לכל המשתמשים: `Hemora123!`** — רק כתובת הדוא״ל משתנה.
ניתן לשנות אותה ב-`.env` דרך `DEFAULT_USER_PASSWORD`.

| תפקיד | דוא״ל | מה רואה |
|---|---|---|
| מנהל מערכת | `admin@hemora.local` | כל 6 המטופלים |
| רופא א׳ | `doctor1@hemora.local` | 2 מטופלים משויכים |
| רופא ב׳ | `doctor2@hemora.local` | מטופל אחד — **רשימה שונה מרופא א׳** |
| רופא ג׳ | `doctor3@hemora.local` | 3 מטופלי מרפאת המרכז |
| מרפאה — צפון | `clinic@hemora.local` | 3 מטופלי מרפאת הצפון |
| מרפאה — מרכז | `clinic2@hemora.local` | 3 מטופלי מרפאת המרכז |
| מטופל | `patient@hemora.local` | את עצמו בלבד |

במסך ההתחברות יש כפתורי כניסה מהירה — לחיצה אחת מחברת.

> החשבונות והסיסמאות מיועדים לפיתוח ולהדגמה בלבד.
> כל ששת המטופלים בדויים ומסומנים `DEMO DATA`.
>
> **כל הנתונים במאגר סינתטיים — אין בו מידע רפואי או אישי אמיתי. סיסמת ההדגמה מיועדת לשימוש מקומי בלבד; אין להשתמש בה בסביבה אמיתית.**
>
> *English: all data in this repository is synthetic — there is no real medical or personal data. The demo password is for local demo use only; never use it in a real deployment.*

**רופא א׳ ורופא ב׳ שייכים לאותה מרפאה אך מקבלים רשימות שונות** — כך אפשר לראות
מיד את ההפרדה ברמת הרופא ואת ההפרדה ברמת המרפאה, בלי להסביר.

---

## מבנה

```text
hemora/
├── backend/       FastAPI, SQLAlchemy, Alembic, pytest
├── frontend/      React, TypeScript, Vite, Tailwind, Vitest, Playwright
├── docs/          תיעוד הגשה, אבטחה, ארכיטקטורה ותסריט הצגה
├── sample-data/   קבצי CSV/XLSX לתרחישי ההדגמה
├── docker-compose.yml
├── .env.example
├── SECURITY.md
└── LICENSE
```

---

## מנועים מרכזיים

- **`ClinicalAnalysisEngine`** — מסווג `NORMAL` / `LOW` / `HIGH` / `CRITICAL` /
  `UNKNOWN_REFERENCE` / `UNVERIFIED` ושומר `HEMORA-CLINICAL-1.0.0`
- **`ReferenceRangeService`** — קדימות לטווח המעבדה, אחריו הגדרת מעבדה,
  ורק אז טווח הדגמה כללי — שמסומן ככזה בממשק
- **`UnitConversionService`** — משווה רק לאחר המרה דטרמיניסטית מאושרת;
  אחרת `NOT_COMPARABLE`
- **`TestComparisonEngine`** — קובע "השתפר" לפי **התקרבות לטווח הייחוס**,
  לא לפי עלייה או ירידה במספר
- **`LongitudinalTrendService`** — מסכם רצפים משלוש בדיקות ומעלה, בלי לחזות מחלה
- **`PanelCompletenessService`** — מבדיל בין חסר לחריג
- **`RecommendationEngine`** — המלצות כלליות מבוססות כללים בלבד
- **`ExplanationService`** — בונה מהנתונים השמורים את התשובה ל"למה HEMORA מציגה את זה?"

הלוגיקה **דטרמיניסטית ולא מבוססת AI**, כדי שכל סיווג יהיה ניתן להסבר ולשחזור.

---

## אבטחה

Argon2, JWT עם access/refresh, RBAC בצד השרת, הגבלת קצב על ההתחברות,
CORS מוגבל, כותרות אבטחה, ORM פרמטרי, הצפנת תעודת זהות עם HMAC נפרד לחיפוש,
הסתרה בממשק ו-Audit מסונן. אין לשמור סודות במאגר.

פירוט מלא כולל מטריצת הרשאות: [`docs/SECURITY_HE.md`](docs/SECURITY_HE.md)

---

## בדיקות

| שכבה | פקודה | תוצאה |
|---|---|---|
| Backend | `cd backend && pytest -q` | **86 עוברות** |
| Frontend | `cd frontend && npm test` | **3 עוברות** |
| בנייה | `cd frontend && npm run build` | ללא שגיאות |
| E2E | ראו למטה | **10 עוברות** |

```bash
# E2E — דורש backend פעיל עם seed
cd backend && LOGIN_RATE_LIMIT=200/minute uvicorn app.main:app --port 8000
cd frontend && npx playwright install chromium && npx playwright test --workers=1
```

ה-E2E מבצע יותר מ-10 התחברויות בדקה ולכן דורש הרפיה של `LOGIN_RATE_LIMIT`;
ברירת המחדל `10/minute` נשארת בתוקף בכל סביבה אחרת.

---

## API

`/api/auth` · `/api/patients` · `/api/patients/{id}/tests` · `/api/patients/{id}/trends` ·
`/api/patients/{id}/doctors` · `/api/tests` · `/api/tests/{id}/analysis` ·
`/api/tests/{id}/comparison` · `/api/tests/{id}/results/{rid}/explanation` ·
`/api/summary` · `/api/clinics` · `/api/analytes` · `/api/import` · `/api/alerts` ·
`/api/admin/*` · `/api/audit` · `/api/reports/{id}.pdf|.csv`

תיעוד אינטראקטיבי: `http://localhost:8000/docs`

---

## תיעוד הגשה

| מסמך | תוכן |
|---|---|
| [`PROJECT_OVERVIEW_HE.md`](docs/PROJECT_OVERVIEW_HE.md) | סקירה כללית |
| [`ARCHITECTURE_HE.md`](docs/ARCHITECTURE_HE.md) | ארכיטקטורה ודיאגרמות |
| [`DATABASE_DESIGN_HE.md`](docs/DATABASE_DESIGN_HE.md) | סכימה ו-ER |
| [`CLINICAL_LOGIC_HE.md`](docs/CLINICAL_LOGIC_HE.md) | האלגוריתם הקליני |
| [`SECURITY_HE.md`](docs/SECURITY_HE.md) | הרשאות ואבטחה |
| [`TEST_PLAN_HE.md`](docs/TEST_PLAN_HE.md) | תוכנית בדיקות |
| [`USER_GUIDE_HE.md`](docs/USER_GUIDE_HE.md) | מדריך למשתמש |
| [`REGULATORY_AND_LIMITATIONS_HE.md`](docs/REGULATORY_AND_LIMITATIONS_HE.md) | מגבלות ורגולציה |
| [`PRESENTATION_SCRIPT_HE.md`](docs/PRESENTATION_SCRIPT_HE.md) | **תסריט הצגה לכיתה** |

---

## מגבלות ועבודה עתידית

זהו אב־טיפוס לימודי ולא מכשיר רפואי מאושר. לפני שימוש עם מידע אמיתי נדרשים
אימות קליני ורגולטורי, מערכת ניהול מפתחות, MFA, מנגנון ביטול refresh tokens,
הגבלת קצב מבוזרת, ניטור, גיבוי, התאוששות, בדיקות חדירה ותהליך איכות רפואי מלא.

ייבוא PDF אינו מיושם, משום שאסור לשמור חילוץ לא מאומת; ייבוא CSV/XLSX מיושם
עם תצוגה מקדימה ואישור מפורש.

---

## הצהרה רפואית

> HEMORA היא מערכת תומכת מידע ואינה מהווה אבחנה רפואית, ייעוץ רפואי או תחליף
> לבדיקה ולהחלטה של איש מקצוע רפואי. טווחי ייחוס עשויים להשתנות בין מעבדות
> ובין מטופלים.
