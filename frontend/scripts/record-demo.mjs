// Records responses from a running, seeded backend into src/demo/fixtures.json
// (used by the static demo build, VITE_DEMO=true). Usage: node scripts/record-demo.mjs [apiBase]
import { writeFileSync, mkdirSync } from "node:fs";

const base = process.argv[2] || "http://localhost:8000/api";
const password = "Hemora123!";
const users = ["admin", "doctor1", "doctor2", "doctor3", "clinic", "clinic2", "patient"].map((u) => `${u}@hemora.local`);
const out = { users: {}, byRole: {} };
mkdirSync("public/demo/reports", { recursive: true });

async function call(token, path, raw = false) {
  const r = await fetch(base + path, { headers: { Authorization: `Bearer ${token}` } });
  if (!r.ok) return null;
  return raw ? Buffer.from(await r.arrayBuffer()) : r.json();
}

for (const email of users) {
  const res = await fetch(base + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const login = await res.json();
  const t = login.access_token;
  const data = {};
  const put = (p, v) => { if (v !== null && v !== undefined) data[p] = v; };
  put("/summary", await call(t, "/summary"));
  put("/clinics", await call(t, "/clinics"));
  put("/alerts", await call(t, "/alerts"));
  put("/analytes", await call(t, "/analytes"));
  const patients = await call(t, "/patients?search=");
  put("/patients?search=", patients);
  if (login.role === "ADMIN") {
    put("/audit", await call(t, "/audit"));
    put("/admin/users", await call(t, "/admin/users"));
    for (const r of ["analytes", "laboratories", "reference-ranges", "units", "clinics"]) put(`/admin/${r}`, await call(t, `/admin/${r}`));
  }
  const analytes = data["/analytes"] || [];
  for (const p of patients?.items || []) {
    put(`/patients/${p.id}`, await call(t, `/patients/${p.id}`));
    put(`/patients/${p.id}/doctors`, await call(t, `/patients/${p.id}/doctors`));
    const tests = await call(t, `/patients/${p.id}/tests`);
    put(`/patients/${p.id}/tests`, tests);
    for (const a of analytes) {
      const code = a.code || a.analyte_code;
      if (code) put(`/patients/${p.id}/trends?code=${code}`, await call(t, `/patients/${p.id}/trends?code=${code}`));
    }
    for (const ts of tests || []) {
      const detail = await call(t, `/tests/${ts.id}`);
      put(`/tests/${ts.id}`, detail);
      put(`/tests/${ts.id}/analysis`, await call(t, `/tests/${ts.id}/analysis`));
      put(`/tests/${ts.id}/comparison`, await call(t, `/tests/${ts.id}/comparison`));
      for (const r of detail?.results || [])
        put(`/tests/${ts.id}/results/${r.id}/explanation`, await call(t, `/tests/${ts.id}/results/${r.id}/explanation`));
      if (login.role === "ADMIN" || login.role === "DOCTOR") {
        for (const fmt of ["pdf", "csv"]) {
          const buf = await call(t, `/reports/${ts.id}.${fmt}`, true);
          if (buf) writeFileSync(`public/demo/reports/${ts.id}.${fmt}`, buf);
        }
      }
    }
  }
  out.users[email] = { role: login.role };
  out.byRole[email] = data;
  console.log(email, login.role, Object.keys(data).length, "endpoints");
}
writeFileSync("src/demo/fixtures.json", JSON.stringify(out));
