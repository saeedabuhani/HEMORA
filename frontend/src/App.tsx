import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Bell,
  Download,
  FilePlus2,
  FlaskConical,
  Home,
  LogOut,
  Menu,
  Plus,
  Search,
  Settings,
  Shield,
  Upload,
  Users,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, Patient } from "./api";
import { ShieldCheck } from "lucide-react";
import {
  ChevronLeft,
  Disclaimer,
  Empty,
  ErrorState,
  Logo,
  Skeleton,
  SourceNotice,
  StatusBadge,
  TrendLabel,
} from "./components";
import NewPatient from "./NewPatient";
import NewTest from "./NewTest";
import {Management, AlertCenter} from "./Management";
type Role = "ADMIN" | "DOCTOR" | "CLINIC" | "PATIENT";
const ALL_ROLES: Role[] = ["ADMIN", "DOCTOR", "CLINIC", "PATIENT"];
const STAFF: Role[] = ["ADMIN", "DOCTOR", "CLINIC"];
// A single source of truth for which role may reach which screen. The server
// enforces the same rules; this only keeps the UI honest.
const nav = [
  { path: "/", label: "לוח בקרה", Icon: Home, roles: ALL_ROLES },
  { path: "/patients", label: "מטופלים", Icon: Users, roles: STAFF },
  { path: "/import", label: "ייבוא בדיקות", Icon: Upload, roles: STAFF },
  { path: "/alerts", label: "מרכז התראות", Icon: Bell, roles: ALL_ROLES },
  { path: "/admin", label: "ניהול וביקורת", Icon: Settings, roles: ["ADMIN"] as Role[] },
] as const;
export const currentRole = (): Role =>
  (sessionStorage.getItem("role") as Role) || "PATIENT";
const ROLE_HE: Record<Role, string> = {
  ADMIN: "מנהל מערכת",
  DOCTOR: "רופא",
  CLINIC: "מרפאה",
  PATIENT: "מטופל",
};
const SCOPE_HE: Record<Role, string> = {
  ADMIN: "כמנהל מערכת מוצגים כל המטופלים הרשומים במערכת.",
  DOCTOR: "כרופא מוצגים רק המטופלים המשויכים אליך.",
  CLINIC: "כמרפאה מוצגים רק המטופלים המשויכים למרפאה שלך.",
  PATIENT: "מוצג התיק האישי שלך בלבד.",
};
function Login() {
  const navg = useNavigate();
  const [email, setEmail] = useState("doctor1@hemora.local");
  const [password, setPassword] = useState("Hemora123!");
  const [error, setError] = useState("");
  const signIn = async (address: string, secret: string) => {
    setError("");
    try {
      const r = await api.login(address, secret);
      sessionStorage.setItem("access_token", r.access_token);
      sessionStorage.setItem("role", r.role);
      navg("/");
    } catch (x) {
      setError((x as Error).message);
    }
  };
  const login = async (e: FormEvent) => {
    e.preventDefault();
    await signIn(email, password);
  };
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#d8f1ee,transparent_35%),linear-gradient(135deg,#f8fbfb,#edf5f5)] p-5">
      <div className="mx-auto grid min-h-[calc(100vh-2.5rem)] max-w-6xl overflow-hidden rounded-[2rem] bg-white shadow-2xl lg:grid-cols-[1.1fr_.9fr]">
        <section className="relative hidden bg-ink p-14 text-white lg:flex lg:flex-col lg:justify-between">
          <Logo />
          <div>
            <div className="mb-8 h-px w-20 bg-brand-500" />
            <h1 className="max-w-lg text-5xl font-black leading-tight">
              הבדיקות שלך.
              <br />
              הסיפור שמאחורי המספרים.
            </h1>
            <p className="mt-6 max-w-md text-lg leading-8 text-slate-300">
              מעקב ברור, השוואה אחראית ושקיפות מלאה לגבי הבסיס לכל ממצא.
            </p>
          </div>
          <p className="text-sm text-slate-400">
            מערכת הדגמה לימודית · לא מכשיר רפואי מאושר
          </p>
        </section>
        <section className="flex items-center p-7 sm:p-14">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-10 lg:hidden">
              <Logo />
            </div>
            <p className="text-sm font-bold text-brand-700">ברוכים הבאים</p>
            <h2 className="mt-2 text-3xl font-black">כניסה מאובטחת ל-HEMORA</h2>
            <p className="mt-2 text-slate-500">
              הזינו את פרטי המשתמש או בחרו חשבון הדגמה.
            </p>
            <form onSubmit={login} className="mt-8 space-y-5">
              <label>
                <span className="label">כתובת דוא״ל</span>
                <input
                  className="field"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="username"
                />
              </label>
              <label>
                <span className="label">סיסמה</span>
                <input
                  className="field"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </label>
              {error && (
                <div
                  role="alert"
                  className="rounded-xl bg-red-50 p-3 text-sm text-red-800"
                >
                  {error}
                </div>
              )}
              <button
                className="btn-primary w-full"
                disabled={login === undefined}
              >
                כניסה למערכת
                <ChevronLeft className="h-4 w-4" />
              </button>
            </form>
            <div className="mt-7">
              <p className="mb-3 text-sm font-bold">כניסה מהירה להדגמה</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  ["מנהל מערכת", "admin@hemora.local", "כל המטופלים"],
                  ["רופא א׳", "doctor1@hemora.local", "2 מטופלים משויכים"],
                  ["רופא ב׳", "doctor2@hemora.local", "מטופל אחד בלבד"],
                  ["מרפאה", "clinic@hemora.local", "3 מטופלי המרפאה"],
                  ["מטופל", "patient@hemora.local", "התיק שלו בלבד"],
                ].map(([label, value, hint]) => (
                  <button
                    key={value}
                    type="button"
                    aria-label={`כניסת הדגמה: ${label}`}
                    className="btn-soft flex-col items-start !py-2 text-right text-sm"
                    onClick={() => {
                      setEmail(value);
                      void signIn(value, password);
                    }}
                  >
                    <span className="font-bold">{label}</span>
                    <span className="text-xs font-normal text-slate-500">
                      {hint}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
function Layout() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [headerSearch, setHeaderSearch] = useState("");
  const role = currentRole();
  const navg = useNavigate();
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]" dir="rtl">
      <aside
        className={`${open ? "block" : "hidden"} fixed inset-y-0 right-0 z-40 w-64 bg-ink p-5 text-white lg:sticky lg:top-0 lg:block lg:h-screen`}
      >
        <Logo compact />
        <nav className="mt-10 space-y-1">
          {nav
            .filter((item) => item.roles.includes(role))
            .map(({ path, label, Icon }) => (
              <NavLink
                key={path}
                to={path}
                end={path === "/"}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold ${isActive ? "bg-brand-600 text-white" : "text-slate-300 hover:bg-white/10"}`
                }
              >
                <Icon className="h-5 w-5" />
                {label}
              </NavLink>
            ))}
        </nav>
        <button
          className="absolute bottom-5 right-5 left-5 flex items-center gap-2 rounded-xl p-3 text-sm text-slate-300 hover:bg-white/10"
          onClick={() => {
            sessionStorage.clear();
            queryClient.clear();
            navg("/login");
          }}
        >
          <LogOut className="h-4 w-4" />
          יציאה
        </button>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex h-18 items-center justify-between border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur sm:px-7">
          <button
            className="btn-soft lg:hidden"
            aria-label="פתיחת תפריט"
            onClick={() => setOpen(!open)}
          >
            <Menu />
          </button>
          <form
            className="desktop-only relative w-full max-w-md"
            onSubmit={(event) => {
              event.preventDefault();
              navg("/patients", { state: { search: headerSearch } });
            }}
          >
            <button
              type="submit"
              aria-label="ביצוע חיפוש"
              className="absolute right-2 top-2 rounded-lg p-1.5 text-slate-400 hover:text-brand-700"
            >
              <Search className="h-4 w-4" />
            </button>
            <input
              className="field pr-10"
              value={headerSearch}
              onChange={(event) => setHeaderSearch(event.target.value)}
              placeholder="חיפוש מטופל או מספר בדיקה"
              aria-label="חיפוש"
            />
          </form>
          <div className="flex items-center gap-3">
            <NavLink
              to="/alerts"
              aria-label="התראות"
              className="rounded-xl border p-2"
            >
              <Bell className="h-5 w-5" />
            </NavLink>
            <div className="text-left text-xs">
              <b>משתמש הדגמה</b>
              <div className="text-slate-500">{ROLE_HE[role]}</div>
            </div>
          </div>
        </header>
        <main className="min-h-[calc(100vh-132px)] p-4 sm:p-7">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/patients" element={<Patients />} />
            <Route path="/patients/new" element={<NewPatient />} />
            <Route path="/patients/:id/new-test" element={<NewTest />} />
            <Route path="/patients/:id" element={<PatientPage />} />
            <Route path="/tests/:id" element={<TestPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/alerts" element={<AlertCenter />} />
            <Route path="/admin" element={<Management />} />
          </Routes>
        </main>
        <Disclaimer />
      </div>
    </div>
  );
}
function Dashboard() {
  const role = currentRole();
  const q = useQuery({ queryKey: ["patients"], queryFn: () => api.patients() });
  const s = useQuery({ queryKey: ["summary"], queryFn: () => api.summary() });
  if (q.isLoading) return <Skeleton />;
  if (q.error)
    return (
      <ErrorState
        message={(q.error as Error).message}
        onRetry={() => q.refetch()}
      />
    );
  const items = q.data?.items || [];
  return (
    <div>
      <div className="mb-7 flex items-end justify-between">
        <div>
          <p className="text-sm font-bold text-brand-700">סקירה קלינית</p>
          <h1 className="text-3xl font-black">לוח הבקרה</h1>
          <p className="mt-2 text-slate-500">
            מעקב מרוכז אחר נתוני ההדגמה והבדיקות האחרונות.
          </p>
        </div>
        {role !== "PATIENT" && (
          <NavLink to="/patients/new" className="btn-primary">
            <Plus className="h-4 w-4" />
            מטופל חדש
          </NavLink>
        )}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["מטופלים", s.data?.patients ?? items.length, Users, ""],
          [
            "בדיקות היסטוריות",
            s.data?.tests ?? items.reduce((a, p) => a + p.test_count, 0),
            FlaskConical,
            "",
          ],
          [
            "תוצאות מחוץ לטווח",
            s.data?.abnormal_results ?? "—",
            AlertCircle,
            `${s.data?.open_alerts ?? 0} התראות פתוחות`,
          ],
          [
            "איכות נתונים ממוצעת",
            s.data?.average_quality != null ? `${s.data.average_quality}%` : "—",
            Shield,
            "אינה ציון בריאות",
          ],
        ].map(([l, v, I, hint]: any) => (
          <div className="card p-5" key={l}>
            <I className="mb-5 text-brand-600" />
            <div className="text-3xl font-black">{v}</div>
            <div className="mt-1 text-sm text-slate-500">{l}</div>
            {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
          </div>
        ))}
      </div>
      <section className="card mt-6 overflow-hidden">
        <div className="flex items-center justify-between border-b p-5">
          <h2 className="text-lg font-bold">
            {role === "PATIENT" ? "התיק שלי" : "מטופלים אחרונים"}
          </h2>
          {role !== "PATIENT" && (
            <NavLink to="/patients" className="text-sm font-bold text-brand-700">
              לכל המטופלים
            </NavLink>
          )}
        </div>
        <PatientTable items={items.slice(0, 5)} />
      </section>
    </div>
  );
}
function PatientTable({ items }: { items: Patient[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[650px] text-right">
        <thead className="bg-slate-50 text-sm text-slate-500">
          <tr>
            <th className="p-4">מטופל</th>
            <th>תעודת זהות</th>
            <th>בדיקות</th>
            <th>בדיקה אחרונה</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id} className="border-t">
              <td className="p-4">
                <div className="font-bold">
                  {p.first_name} {p.last_name}
                </div>
                {p.demo && (
                  <span className="text-xs font-bold text-brand-700">
                    DEMO DATA
                  </span>
                )}
              </td>
              <td>{p.masked_national_id}</td>
              <td>{p.test_count}</td>
              <td>
                {p.last_test_date
                  ? new Date(p.last_test_date).toLocaleDateString("he-IL")
                  : "אין"}
              </td>
              <td>
                <NavLink className="btn-soft" to={`/patients/${p.id}`}>
                  פתיחה
                  <ChevronLeft className="h-4 w-4" />
                </NavLink>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Patients() {
  const location = useLocation();
  const [search, setSearch] = useState(
    (location.state as { search?: string } | null)?.search || "",
  );
  const role = currentRole();
  const q = useQuery({
    queryKey: ["patients", search],
    queryFn: () => api.patients(search),
  });
  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black">מטופלים</h1>
          <p className="mt-1 text-slate-500">
            חיפוש מאובטח לפי שם, תעודת זהות או מספר בדיקה.
          </p>
        </div>
        {role !== "PATIENT" && (
          <NavLink to="/patients/new" className="btn-primary">
            <Plus />
            מטופל חדש
          </NavLink>
        )}
      </div>
      <div className="mb-4 flex items-center gap-3 rounded-xl bg-brand-50 p-4 text-sm text-ink">
        <ShieldCheck className="h-5 w-5 shrink-0 text-brand-700" />
        <span>
          <b>היקף הצפייה שלך: </b>
          {SCOPE_HE[role]} סה״כ {q.data?.total ?? 0} מטופלים.
        </span>
      </div>
      <div className="card mb-4 p-4">
        <input
          className="field"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="הקלידו לחיפוש..."
        />
      </div>
      {q.isLoading ? (
        <Skeleton />
      ) : q.error ? (
        <ErrorState message={(q.error as Error).message} />
      ) : (
        <div className="card overflow-hidden">
          <PatientTable items={q.data?.items || []} />
        </div>
      )}
    </div>
  );
}
function CareTeam({ patientId }: { patientId: string }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const assigned = useQuery({
    queryKey: ["patient-doctors", patientId],
    queryFn: () => api.patientDoctors(patientId),
  });
  const doctors = useQuery({ queryKey: ["users"], queryFn: () => api.users() });
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["patient-doctors", patientId] });
    void queryClient.invalidateQueries({ queryKey: ["patients"] });
  };
  const run = async (action: Promise<unknown>) => {
    setError("");
    try {
      await action;
      refresh();
    } catch (x) {
      setError((x as Error).message);
    }
  };
  const assignedIds = new Set((assigned.data || []).map((d) => d.doctor_user_id));
  const available = (doctors.data || []).filter(
    (u) => u.role === "DOCTOR" && !assignedIds.has(u.id),
  );
  return (
    <div className="card mb-5 p-5">
      <h2 className="font-bold">רופאים מטפלים</h2>
      <p className="mt-1 text-sm text-slate-500">
        רופא רואה רק מטופלים המשויכים אליו. כל שינוי כאן נרשם ביומן הביקורת.
      </p>
      {error && (
        <div role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}
      <ul className="mt-3 space-y-2">
        {(assigned.data || []).map((doctor) => (
          <li
            key={doctor.doctor_user_id}
            className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-3 text-sm"
          >
            <span className="font-semibold">{doctor.email}</span>
            <button
              className="btn-soft !px-3 !py-1.5 text-xs"
              onClick={() => run(api.unassignDoctor(patientId, doctor.doctor_user_id))}
            >
              ביטול שיוך
            </button>
          </li>
        ))}
        {assigned.data?.length === 0 && (
          <li className="text-sm text-slate-500">אין רופא משויך למטופל זה.</li>
        )}
      </ul>
      {available.length > 0 && (
        <label className="mt-4 block">
          <span className="label">שיוך רופא נוסף</span>
          <select
            className="field"
            value=""
            onChange={(e) => {
              if (e.target.value) run(api.assignDoctor(patientId, Number(e.target.value)));
            }}
          >
            <option value="">בחרו רופא…</option>
            {available.map((doctor) => (
              <option key={doctor.id} value={doctor.id}>
                {doctor.email}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}

function PatientPage() {
  const { id } = useParams();
  const p = useQuery({
    queryKey: ["patient", id],
    queryFn: () => api.patient(id!),
  });
  const tests = useQuery({
    queryKey: ["tests", id],
    queryFn: () => api.tests(id!),
  });
  const trend = useQuery({
    queryKey: ["trend", id],
    queryFn: () => api.trends(id!),
  });
  const role = currentRole();
  const failure = p.error || tests.error;
  if (failure) return <ErrorState message={(failure as Error).message} />;
  if (p.isLoading || tests.isLoading || !p.data) return <Skeleton />;
  const patient = p.data;
  return (
    <div>
      <NavLink
        to="/patients"
        className="mb-4 inline-flex items-center text-sm font-bold text-brand-700"
      >
        חזרה למטופלים
      </NavLink>
      <div className="card mb-5 flex flex-wrap items-center justify-between gap-5 p-6">
        <div>
          <div className="mb-2 text-xs font-bold text-brand-700">
            {patient.demo ? "DEMO DATA" : "רשומה רפואית"}
          </div>
          <h1 className="text-3xl font-black">
            {patient.first_name} {patient.last_name}
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            {patient.masked_national_id} · {patient.test_count} בדיקות · בדיקה
            אחרונה{" "}
            {patient.last_test_date
              ? new Date(patient.last_test_date).toLocaleDateString("he-IL")
              : "אין"}
          </p>
          {patient.clinic_name && (
            <p className="mt-1 text-sm text-slate-500">
              מרפאה מטפלת: <b>{patient.clinic_name}</b>
            </p>
          )}
        </div>
        {role !== "PATIENT" && (
          <NavLink to={`/patients/${id}/new-test`} className="btn-primary">
            <FilePlus2 />
            הוספת בדיקה
          </NavLink>
        )}
      </div>
      {(role === "ADMIN" || role === "CLINIC") && <CareTeam patientId={id!} />}
      {trend.data?.points?.length > 1 && (
        <div className="card mb-5 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-bold">מגמת HGB לאורך זמן</h2>
              <p className="text-sm text-slate-500">
                ללא חיזוי עתידי; מגמה תיאורית בלבד.
              </p>
            </div>
            <Activity className="text-brand-600" />
          </div>
          <div className="h-64" dir="ltr">
            <ResponsiveContainer>
              <LineChart data={trend.data.points}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#0d746f"
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      <h2 className="mb-3 text-xl font-bold">היסטוריית בדיקות</h2>
      {!tests.data?.length ? (
        <Empty
          title="עדיין לא קיימות בדיקות למטופל זה"
          body="אפשר להוסיף בדיקה ידנית או לייבא קובץ מעבדה."
        />
      ) : (
        <div className="grid gap-3">
          {tests.data.map((t) => (
            <NavLink
              to={`/tests/${t.id}`}
              key={t.id}
              className="card flex items-center justify-between p-5 transition hover:border-brand-500"
            >
              <div>
                <b>
                  {t.panel || "בדיקת דם"} ·{" "}
                  {new Date(t.test_date).toLocaleDateString("he-IL")}
                </b>
                <p className="mt-1 text-sm text-slate-500">
                  {t.accession_number} · {t.results_count} מדדים
                </p>
              </div>
              <ChevronLeft />
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}
function ExplanationModal({
  testId,
  resultId,
  onClose,
}: {
  testId: string;
  resultId: number;
  onClose: () => void;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const q = useQuery({
    queryKey: ["explanation", testId, resultId],
    queryFn: () => api.explanation(testId, resultId),
  });
  useEffect(() => {
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  const row = (label: string, value: ReactNode) =>
    value === null || value === undefined || value === "" ? null : (
      <div className="flex justify-between gap-4 border-b border-slate-100 py-2 last:border-0">
        <dt className="text-slate-500">{label}</dt>
        <dd className="text-left font-semibold">{value}</dd>
      </div>
    );
  const d = q.data;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4"
      onClick={onClose}
    >
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="explanation-title"
        tabIndex={-1}
        dir="rtl"
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id="explanation-title" className="text-2xl font-black">
            למה HEMORA מציגה את זה?
          </h2>
          <button className="btn-soft" onClick={onClose} aria-label="סגירה">
            סגירה
          </button>
        </div>
        {q.isLoading && <Skeleton />}
        {q.error && <ErrorState message={(q.error as Error).message} />}
        {d && (
          <div className="mt-4 space-y-5 text-sm">
            <div>
              <p className="text-lg font-bold">
                {d.analyte.code} · {d.analyte.name_he}
              </p>
              <p className="mt-1 text-slate-500">{d.analyte.description_he}</p>
            </div>
            <div className="rounded-xl bg-brand-50 p-4">
              <p className="font-semibold text-ink">{d.classification_reason}</p>
              {d.comparison?.rule_he && (
                <p className="mt-2 text-ink">{d.comparison.rule_he}</p>
              )}
            </div>
            <dl>
              {row("ערך שנמדד", `${d.measured.value} ${d.measured.unit}`)}
              {row(
                "ערך מנורמל",
                d.measured.normalized_value != null &&
                  d.measured.normalized_unit !== d.measured.unit
                  ? `${d.measured.normalized_value} ${d.measured.normalized_unit}`
                  : null,
              )}
              {row(
                "טווח ייחוס",
                d.reference.min != null
                  ? `${d.reference.min}–${d.reference.max}`
                  : "לא התקבל טווח ייחוס",
              )}
              {row("מקור טווח הייחוס", d.reference.source_he)}
              {row(
                "סף קריטי",
                d.reference.critical_low != null || d.reference.critical_high != null
                  ? `${d.reference.critical_low ?? "—"} / ${d.reference.critical_high ?? "—"}`
                  : null,
              )}
              {row("סיווג", d.status_he)}
              {row("תאריך הבדיקה", new Date(d.test_date).toLocaleDateString("he-IL"))}
              {row(
                "ערך קודם",
                d.comparison?.previous_value != null
                  ? `${d.comparison.previous_value} ${d.comparison.previous_unit ?? ""}`
                  : null,
              )}
              {row(
                "תאריך קודם",
                d.comparison?.previous_date
                  ? new Date(d.comparison.previous_date).toLocaleDateString("he-IL")
                  : null,
              )}
              {row(
                "מספר ימים בין הבדיקות",
                d.comparison?.days_between != null ? String(d.comparison.days_between) : null,
              )}
              {row("מגמה", d.comparison?.trend_he)}
              {row("אמינות ההשוואה", d.comparison?.reliability)}
              {row("איכות הנתון", d.data_quality)}
              {row("גרסת אלגוריתם", d.algorithm_version)}
            </dl>
            <div>
              <h3 className="mb-2 font-bold">מגבלות</h3>
              <ul className="list-disc space-y-1 pr-5 text-slate-600">
                {d.limitations.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TestPage() {
  const { id } = useParams();
  const t = useQuery({ queryKey: ["test", id], queryFn: () => api.test(id!) });
  const a = useQuery({
    queryKey: ["analysis", id],
    queryFn: () => api.analysis(id!),
  });
  const c = useQuery({
    queryKey: ["comparison", id],
    queryFn: () => api.comparison(id!),
  });
  const [professional, setProfessional] = useState(false);
  const [explaining, setExplaining] = useState<number | null>(null);
  const [downloadState, setDownloadState] = useState<"" | "pdf" | "csv">("");
  const [downloadError, setDownloadError] = useState("");
  const failure = t.error || a.error;
  if (failure) return <ErrorState message={(failure as Error).message} />;
  if (t.isLoading || a.isLoading || !t.data) return <Skeleton />;
  const test = t.data;
  const counts = a.data?.summary?.counts || {};
  return (
    <div>
      <NavLink
        to={`/patients/${test.patient_id}`}
        className="text-sm font-bold text-brand-700"
      >
        חזרה למטופל
      </NavLink>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-brand-700">
            {test.accession_number}
          </p>
          <h1 className="text-3xl font-black">
            {test.panel || "בדיקת דם"} ·{" "}
            {new Date(test.test_date).toLocaleDateString("he-IL")}
          </h1>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-soft"
            onClick={() => setProfessional(!professional)}
          >
            {professional ? "תצוגת מטופל" : "תצוגה מקצועית"}
          </button>
          <button
            className="btn-primary"
            disabled={downloadState !== ""}
            onClick={async () => {
              setDownloadError("");
              setDownloadState("pdf");
              try {
                await api.downloadReport(test.id, "pdf");
              } catch (error) {
                setDownloadError((error as Error).message);
              } finally {
                setDownloadState("");
              }
            }}
          >
            <Download className="h-4 w-4" />
            {downloadState === "pdf" ? "מכין דוח..." : "דוח PDF"}
          </button>
          <button
            className="btn-soft"
            disabled={downloadState !== ""}
            onClick={async () => {
              setDownloadError("");
              setDownloadState("csv");
              try {
                await api.downloadReport(test.id, "csv");
              } catch (error) {
                setDownloadError((error as Error).message);
              } finally {
                setDownloadState("");
              }
            }}
          >
            {downloadState === "csv" ? "מכין קובץ..." : "ייצוא CSV"}
          </button>
        </div>
      </div>
      {downloadError && (
        <div
          role="alert"
          className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-800"
        >
          {downloadError}
        </div>
      )}
      <div className="my-5 grid gap-3 sm:grid-cols-4">
        {[
          ["בטווח", counts.NORMAL || 0, "text-emerald-700"],
          ["חריגים", (counts.LOW || 0) + (counts.HIGH || 0), "text-amber-700"],
          [
            "קריטיים",
            (counts.CRITICAL_LOW || 0) + (counts.CRITICAL_HIGH || 0),
            "text-red-700",
          ],
          ["דורשים אימות", counts.UNVERIFIED || 0, "text-slate-700"],
        ].map(([l, v, color]) => (
          <div className="card p-4" key={l}>
            <div className={`text-3xl font-black ${color}`}>{v}</div>
            <div className="text-sm text-slate-500">{l}</div>
          </div>
        ))}
      </div>
      <div className="card mb-5 p-4">
        <div className="flex items-center justify-between">
          <b>איכות נתוני הבדיקה: {a.data?.summary?.quality_level}</b>
          <span className="text-2xl font-black text-brand-700">
            {a.data?.quality_score}%
          </span>
        </div>
        <p className="mt-2 text-sm text-slate-500">
          {a.data?.summary?.quality_explanation}
        </p>
        {a.data?.summary?.missing?.length > 0 && (
          <div className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
            בדיקת CBC שהוזנה אינה כוללת ערך {a.data.summary.missing.join(", ")}.
            ייתכן שהערך לא הועבר, לא נמדד או לא נכלל בדוח. מומלץ לבדוק את דוח
            המעבדה המקורי.
          </div>
        )}
      </div>
      {explaining !== null && (
        <ExplanationModal
          testId={test.id}
          resultId={explaining}
          onClose={() => setExplaining(null)}
        />
      )}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-right">
            <thead className="bg-slate-50 text-sm text-slate-500">
              <tr>
                <th className="p-4">מדד</th>
                <th>ערך</th>
                <th>טווח ייחוס</th>
                <th>מצב</th>
                <th>הסבר</th>
                {professional && (
                  <>
                    <th>מקור</th>
                    <th>איכות</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {test.results.map((r) => (
                <tr key={r.id} className="border-t align-top">
                  <td className="p-4">
                    <b>{r.code}</b>
                    <div>{r.name_he}</div>
                    <p className="mt-1 max-w-xs text-xs text-slate-500">
                      {r.description_he}
                    </p>
                  </td>
                  <td className="font-bold">
                    {r.value} {r.unit}
                  </td>
                  <td>
                    {r.reference_min != null
                      ? `${r.reference_min}–${r.reference_max}`
                      : "לא התקבל טווח"}
                    <SourceNotice source={r.reference_source} />
                  </td>
                  <td>
                    <StatusBadge status={r.status} />
                  </td>
                  <td>
                    <button
                      className="btn-soft whitespace-nowrap !px-3 !py-1.5 text-xs"
                      onClick={() => setExplaining(r.id)}
                    >
                      למה?
                    </button>
                  </td>
                  {professional && (
                    <>
                      <td className="text-xs">{r.reference_source}</td>
                      <td>{r.quality}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <section className="mt-6">
        <h2 className="mb-3 text-xl font-bold">מה השתנה מהבדיקה הקודמת?</h2>
        {c.data?.previous_test ? (
          <div className="grid gap-3">
            {c.data.items.map((x: any) => (
              <div
                className="card flex flex-wrap items-center justify-between gap-3 p-4"
                key={x.code}
              >
                <div>
                  <b>
                    {x.code} {x.name_he}
                  </b>
                  <p className="mt-1 text-sm text-slate-500">
                    {x.message || `${x.previous} ← ${x.current} ${x.unit}`}
                  </p>
                </div>
                <TrendLabel trend={x.trend} />
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="זוהי הבדיקה הראשונה במערכת"
            body="עדיין אין בסיס להשוואה. לאחר בדיקה נוספת תוצג כאן השוואה מדד-מול-מדד."
          />
        )}
      </section>
      <section className="card mt-6 p-5">
        <h2 className="font-bold">המלצות כלליות</h2>
        {a.data?.recommendations.map((r: any, i: number) => (
          <p className="mt-3 text-sm leading-7" key={i}>
            • {r.text}
          </p>
        ))}
        <p className="mt-4 border-t pt-4 text-xs text-slate-500">
          מקורות מידע חינוכיים: MedlinePlus, NHLBI ומסמכי המעבדה. ההסברים הם
          סיכומים מקוריים ואינם אבחנה.
        </p>
      </section>
    </div>
  );
}
function ImportPage() {
  const navigate = useNavigate();
  const patientQuery = useQuery({
    queryKey: ["patients", "import"],
    queryFn: () => api.patients(),
  });
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [error, setError] = useState("");
  const [patientId, setPatientId] = useState("");
  const [testDate, setTestDate] = useState("");
  const [accession, setAccession] = useState("");
  const upload = async () => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const token = sessionStorage.getItem("access_token");
      const res = await fetch(
        (import.meta.env.VITE_API_URL || "http://localhost:8000/api") +
          "/import/preview",
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: form,
        },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.message);
      setPreview(data);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const confirmImport = async () => {
    if (!patientId || !testDate || !accession || !preview) {
      setError("יש לבחור מטופל, תאריך ומספר בדיקה לפני השמירה.");
      return;
    }
    try {
      const result = await api.createTest({
        patient_id: patientId,
        laboratory_id: 1,
        test_date: testDate,
        accession_number: accession,
        panel: "CBC",
        source: "CSV_IMPORT",
        results: preview.rows.map((row: any) => ({
          analyte_code: row.analyte_code,
          numeric_value: row.numeric_value,
          unit: row.unit,
          reference_min: row.reference_min ? Number(row.reference_min) : null,
          reference_max: row.reference_max ? Number(row.reference_max) : null,
          lab_flag: row.lab_flag || null,
          verified: true,
        })),
      });
      navigate(`/tests/${result.id}`);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <div>
      <h1 className="text-3xl font-black">ייבוא בדיקות</h1>
      <p className="mt-2 text-slate-500">
        אשף ייבוא בטוח: העלאה, מיפוי, תצוגה מקדימה, אימות ואישור מפורש.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-5">
        {[
          "1 העלאה",
          "2 מיפוי עמודות",
          "3 תצוגה מקדימה",
          "4 אימות",
          "5 אישור",
        ].map((s, i) => (
          <div
            className={`rounded-xl border p-3 text-sm font-bold ${i === 0 ? "border-brand-600 bg-brand-50 text-brand-700" : "bg-white text-slate-400"}`}
            key={s}
          >
            {s}
          </div>
        ))}
      </div>
      <div className="card mt-5 p-6">
        <div className="mb-5 grid gap-4 md:grid-cols-3">
          <label>
            <span className="label">מטופל</span>
            <select
              className="field"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
            >
              <option value="">בחירה</option>
              {patientQuery.data?.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="label">תאריך בדיקה</span>
            <input
              className="field"
              type="date"
              value={testDate}
              onChange={(e) => setTestDate(e.target.value)}
            />
          </label>
          <label>
            <span className="label">מספר בדיקה</span>
            <input
              className="field"
              value={accession}
              onChange={(e) => setAccession(e.target.value)}
            />
          </label>
        </div>
        <label className="label">קובץ CSV</label>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="field"
        />
        <button className="btn-primary mt-4" onClick={upload} disabled={!file}>
          <Upload className="h-4 w-4" />
          בדיקת הקובץ
        </button>
        {error && <p className="mt-3 text-red-700">{error}</p>}
      </div>
      {preview && (
        <div className="card mt-5 overflow-hidden">
          <div className="border-b p-4 font-bold">
            תצוגה מקדימה — הנתונים עדיין לא נשמרו
          </div>
          <pre
            className="max-h-96 overflow-auto p-4 text-left text-xs"
            dir="ltr"
          >
            {JSON.stringify(preview, null, 2)}
          </pre>
          <div className="border-t p-4">
            <button
              className="btn-primary"
              disabled={
                preview.errors.length > 0 ||
                !patientId ||
                !testDate ||
                !accession
              }
              onClick={confirmImport}
            >
              אישור מפורש ושמירה
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
function Alerts() {
  const [read, setRead] = useState<string[]>([]);
  return (
    <div>
      <h1 className="text-3xl font-black">מרכז התראות</h1>
      <p className="mt-2 text-slate-500">
        מידע חסר, ערכים לא מאומתים, חריגות חדשות ובעיות ייבוא.
      </p>
      <div className="mt-6 space-y-3">
        {[
          ["חריגה חדשה ב-HGB", "דורש עיון מקצועי", "bg-amber-50"],
          [
            "HGB חסר בבדיקת CBC",
            "יש לבדוק את דוח המעבדה המקורי",
            "bg-slate-50",
          ],
          [
            "יחידות לא נתמכות להשוואה",
            "ההשוואה סומנה כלא מהימנה",
            "bg-slate-50",
          ],
        ].map(([t, b, c]) => (
          <div className={`card ${c} p-5`} key={t}>
            <b>{t}</b>
            <p className="mt-1 text-sm text-slate-600">{b}</p>
            <button
              className="btn-soft mt-3"
              onClick={() => setRead([...read, t])}
              disabled={read.includes(t)}
            >
              {read.includes(t) ? "נקרא" : "סימון כנקרא"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
function Admin() {
  const q = useQuery({ queryKey: ["audit"], queryFn: api.audit });
  if (sessionStorage.getItem("role") !== "ADMIN")
    return <ErrorState message="המסך זמין למנהלי מערכת בלבד." />;
  return (
    <div>
      <h1 className="text-3xl font-black">ניהול וביקורת</h1>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[
          ["קטלוג מדדים", "49 מדדים פעילים"],
          ["מעבדות", "מעבדת הדגמה אחת"],
          ["כללי המלצה", "כללים דטרמיניסטיים"],
        ].map(([a, b]) => (
          <div className="card p-5" key={a}>
            <b>{a}</b>
            <p className="mt-2 text-sm text-slate-500">{b}</p>
            <span className="badge mt-4 bg-brand-50 text-brand-700">
              מוגדר ופעיל
            </span>
          </div>
        ))}
      </div>
      <h2 className="mb-3 mt-8 text-xl font-bold">יומן ביקורת</h2>
      {q.isLoading ? (
        <Skeleton />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[700px] text-right text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="p-3">זמן</th>
                <th>פעולה</th>
                <th>ישות</th>
                <th>משתמש</th>
              </tr>
            </thead>
            <tbody>
              {q.data?.map((x) => (
                <tr className="border-t" key={x.id}>
                  <td className="p-3">
                    {new Date(x.timestamp).toLocaleString("he-IL")}
                  </td>
                  <td>{x.action}</td>
                  <td>
                    {x.entity_type} {x.entity_id}
                  </td>
                  <td>{x.user_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
export default function App() {
  const authenticated = !!sessionStorage.getItem("access_token");
  const location = useLocation();
  if (!authenticated && location.pathname != "/login")
    return <Navigate to="/login" replace />;
  if (authenticated && location.pathname === "/login")
    return <Navigate to="/" replace />;
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<Layout />} />
    </Routes>
  );
}
