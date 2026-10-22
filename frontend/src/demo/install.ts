// Static demo mode (VITE_DEMO=true): replaces the network with responses recorded
// from the real, seeded backend (scripts/record-demo.mjs). Nothing is sent anywhere.
import fixtures from "./fixtures.json";

type Fixtures = { users: Record<string, { role: string }>; byRole: Record<string, Record<string, any>> };
const fx = fixtures as unknown as Fixtures;
const realFetch = window.fetch.bind(window);
const API = (import.meta.env.VITE_API_URL as string | undefined) || "http://localhost:8000/api";
const PASSWORD = "Hemora123!";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const err = (status: number, message: string) => json({ detail: { code: "DEMO", message } }, status);

function emailFromAuth(init?: RequestInit): string | null {
  const h = new Headers(init?.headers);
  const m = /^Bearer demo:(.+)$/.exec(h.get("Authorization") || "");
  return m ? m[1] : null;
}

window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  if (!url.startsWith(API)) return realFetch(input, init);
  const path = url.slice(API.length);
  const method = (init?.method || "GET").toUpperCase();

  if (path === "/auth/login" && method === "POST") {
    const { email, password } = JSON.parse(String(init?.body || "{}"));
    const key = String(email || "").toLowerCase();
    if (fx.users[key] && password === PASSWORD)
      return json({ access_token: `demo:${key}`, refresh_token: `demo:${key}`, role: fx.users[key].role });
    return err(401, "פרטי ההתחברות שגויים");
  }
  const who = emailFromAuth(init);
  if (!who || !fx.byRole[who]) return err(401, "נדרשת התחברות מחדש");
  const data = fx.byRole[who];

  if (method !== "GET") {
    window.dispatchEvent(new CustomEvent("demo-write-blocked"));
    return err(403, "מצב הדגמה: שינויים אינם נשמרים");
  }
  const report = /^\/reports\/([^/]+\.(pdf|csv))$/.exec(path);
  if (report) {
    const id = report[1].split(".")[0];
    if (!Object.keys(data).some((k) => k === `/tests/${id}`)) return err(403, "אין הרשאה לדוח זה");
    return realFetch(`${import.meta.env.BASE_URL}demo/reports/${report[1]}`);
  }
  const search = /^\/patients\?search=(.*)$/.exec(path);
  if (search) {
    const q = decodeURIComponent(search[1]).trim().toLowerCase();
    const all = data["/patients?search="] || { items: [], total: 0 };
    const items = q
      ? all.items.filter((p: any) => `${p.first_name} ${p.last_name} ${p.id}`.toLowerCase().includes(q))
      : all.items;
    return json({ items, total: items.length });
  }
  if (path in data) return json(data[path]);
  return err(path.startsWith("/patients/") || path.startsWith("/tests/") ? 403 : 404, "אין הרשאה לצפות בנתוני מטופל זה");
};

export function mountDemoBanner() {
  const bar = document.createElement("div");
  bar.setAttribute("role", "status");
  bar.dir = "ltr";
  bar.style.cssText =
    "position:fixed;bottom:0;left:0;right:0;z-index:9999;background:#0f172a;color:#fff;font:13px/1.4 system-ui,sans-serif;padding:8px 14px;text-align:center";
  bar.innerHTML =
    'Demo mode – sample data, synthetic patients, changes are not saved. · <a style="color:#5eead4" href="https://github.com/saeedabuhani/HEMORA">View source on GitHub</a>';
  document.body.appendChild(bar);
  window.addEventListener("demo-write-blocked", () => {
    bar.textContent = "Demo mode – this action is disabled in the public demo (nothing is saved).";
  });
}
