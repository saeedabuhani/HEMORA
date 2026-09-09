import { test, expect, Page } from "@playwright/test";

/**
 * End-to-end demo scenarios.
 * Requires the backend running on :8000 with `python -m app.seed` already applied.
 */

const DEMO_BUTTON = {
  admin: "מנהל מערכת",
  doctorA: "רופא א׳",
  doctorB: "רופא ב׳",
  clinic: "מרפאה",
  patient: "מטופל",
} as const;

async function signIn(page: Page, who: keyof typeof DEMO_BUTTON) {
  // An authenticated visitor is redirected away from /login, so drop any
  // existing session before switching roles inside a single test.
  await page.goto("/");
  await page.evaluate(() => sessionStorage.clear());
  await page.goto("/login");
  await page.getByRole("button", { name: `כניסת הדגמה: ${DEMO_BUTTON[who]}`, exact: true }).click();
  await expect(page.getByRole("heading", { name: "לוח הבקרה" })).toBeVisible();
}

async function openPatient(page: Page, name: string) {
  await page.goto("/patients");
  const row = page.locator("tr", { hasText: name });
  await row.getByRole("link", { name: "פתיחה" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
}

test("login screen offers the demo roles", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText("הבדיקות שלך.")).toBeVisible();
  for (const label of Object.values(DEMO_BUTTON)) {
    await expect(page.getByRole("button", { name: `כניסת הדגמה: ${label}`, exact: true })).toBeVisible();
  }
});

/* ---------------------------------------------------------- scenario 1
   Login -> patient -> blood test -> analysis                            */

test("scenario 1: a clinician opens a patient and reads the analysis", async ({ page }) => {
  await signIn(page, "admin");
  await openPatient(page, "דניאל כהן");

  await page.getByText(/DEMO-002-C/).click();

  await expect(page.getByRole("cell", { name: "HGB", exact: false }).first()).toBeVisible();
  await expect(page.getByText("איכות נתוני הבדיקה", { exact: false })).toBeVisible();
  // the permanent medical disclaimer must be present on every screen
  await expect(page.getByText("אינה מהווה אבחנה רפואית", { exact: false })).toBeVisible();
});

/* ---------------------------------------------------------- scenario 2
   A later test is compared against the previous one                     */

test("scenario 2: a follow-up test is compared with the previous one", async ({ page }) => {
  await signIn(page, "admin");
  await openPatient(page, "דניאל כהן");
  await page.getByText(/DEMO-002-C/).click();

  await expect(page.getByRole("heading", { name: "מה השתנה מהבדיקה הקודמת?" })).toBeVisible();
  await expect(page.getByText("השתפר").first()).toBeVisible();
});

test("scenario 2b: the explanation modal is built from the stored data", async ({ page }) => {
  await signIn(page, "admin");
  await openPatient(page, "דניאל כהן");
  await page.getByText(/DEMO-002-C/).click();

  const hgbRow = page.locator("tr", { hasText: "המוגלובין" }).first();
  await hgbRow.getByRole("button", { name: "למה?" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "למה HEMORA מציגה את זה?" })).toBeVisible();
  await expect(dialog.getByText("מקור טווח הייחוס")).toBeVisible();
  await expect(dialog.getByText("ערך קודם")).toBeVisible();
  await expect(dialog.getByText("HEMORA-CLINICAL-1.0.0")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

/* ---------------------------------------------------------- scenario 3
   A CBC without HGB is reported as missing data, not as an abnormality  */

test("scenario 3: a CBC without HGB is reported as missing data", async ({ page }) => {
  await signIn(page, "admin");
  await openPatient(page, "יואב שלום");
  await page.getByText(/DEMO-004/).click();

  await expect(page.getByText("אינה כוללת ערך HGB", { exact: false })).toBeVisible();
  await expect(page.getByText("דוח המעבדה המקורי", { exact: false })).toBeVisible();
});

/* ---------------------------------------------------------- scenario 4
   Report download                                                        */

test("scenario 4: the PDF report downloads", async ({ page }) => {
  await signIn(page, "admin");
  await openPatient(page, "דניאל כהן");
  await page.getByText(/DEMO-002-C/).click();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: /דוח PDF/ }).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/\.pdf$/);
});

/* ---------------------------------------------------------- scenario 5
   The four roles each see a different slice of the data                  */

async function visiblePatientCount(page: Page) {
  await page.goto("/patients");
  // wait for the table to render before counting
  await expect(page.locator("tbody tr").first()).toBeVisible();
  return page.locator("tbody tr").count();
}

test("scenario 5: each role sees only what it is allowed to", async ({ page }) => {
  await signIn(page, "doctorA");
  const doctorAPatients = await visiblePatientCount(page);
  await expect(page.getByText("כרופא מוצגים רק המטופלים המשויכים אליך", { exact: false })).toBeVisible();

  await signIn(page, "doctorB");
  const doctorBPatients = await visiblePatientCount(page);

  await signIn(page, "clinic");
  const clinicPatients = await visiblePatientCount(page);
  await expect(page.getByText("כמרפאה מוצגים רק המטופלים", { exact: false })).toBeVisible();

  await signIn(page, "admin");
  const adminPatients = await visiblePatientCount(page);

  // a doctor sees fewer patients than their clinic, which sees fewer than the admin
  expect(doctorAPatients).toBeLessThan(clinicPatients);
  expect(doctorBPatients).toBeLessThan(clinicPatients);
  expect(clinicPatients).toBeLessThan(adminPatients);
});

test("scenario 5b: a patient sees only their own record and a reduced menu", async ({ page }) => {
  await signIn(page, "patient");
  await expect(page.getByRole("heading", { name: "התיק שלי" })).toBeVisible();
  await expect(page.getByRole("link", { name: "מטופלים" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "ייבוא בדיקות" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "ניהול וביקורת" })).toHaveCount(0);
});

test("scenario 5c: reaching another doctor's patient by URL is refused", async ({ page }) => {
  await signIn(page, "admin");
  await page.goto("/patients");
  // pick a patient the north-clinic doctors are not assigned to
  const href = await page.locator("tbody tr a").last().getAttribute("href");

  await signIn(page, "doctorB");
  await page.goto(href!);
  await expect(page.getByText("אין הרשאה לצפות בנתוני מטופל זה")).toBeVisible();
});

test("admin can reach the audit log and a doctor cannot", async ({ page }) => {
  await signIn(page, "admin");
  await expect(page.getByRole("link", { name: "ניהול וביקורת" })).toBeVisible();

  await signIn(page, "doctorA");
  await expect(page.getByRole("link", { name: "ניהול וביקורת" })).toHaveCount(0);
});
