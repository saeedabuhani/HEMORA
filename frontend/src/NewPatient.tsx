import { FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, NewPatientResult } from "./api";
import { currentRole } from "./App";

export default function NewPatient() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const role = currentRole();
  // Only an admin picks the clinic; for a doctor or a clinic user the server
  // derives it from their own account, so the field would be meaningless.
  const clinics = useQuery({
    queryKey: ["clinics"],
    queryFn: () => api.clinics(),
    enabled: role === "ADMIN",
  });
  const [created, setCreated] = useState<NewPatientResult | null>(null);
  const mutation = useMutation({
    mutationFn: api.createPatient,
    onSuccess: (patient) => {
      // A one-time password must be shown before leaving the page; without one
      // there is nothing to hand over, so go straight to the patient.
      if (patient.account) setCreated(patient);
      else navigate(`/patients/${patient.id}`);
    },
    onError: (e) => setError((e as Error).message),
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body: Record<string, unknown> = Object.fromEntries(
      new FormData(event.currentTarget).entries(),
    );
    if (body.clinic_id) body.clinic_id = Number(body.clinic_id);
    body.create_account = body.create_account === "on";
    mutation.mutate(body);
  };
  if (created?.account) {
    return (
      <div className="mx-auto max-w-2xl">
        <h1 className="text-3xl font-black">המטופל נוצר</h1>
        <p className="mt-2 text-slate-500">
          {created.first_name} {created.last_name} · {created.masked_national_id}
        </p>
        <div className="card mt-6 border-2 border-brand-600 p-6">
          <h2 className="text-xl font-bold">פרטי הכניסה של המטופל</h2>
          <p className="mt-2 text-sm text-amber-800">{created.account.notice}</p>
          <dl className="mt-5 space-y-3">
            <div>
              <dt className="label">שם משתמש</dt>
              <dd className="field select-all font-mono" dir="ltr">
                {created.account.email}
              </dd>
            </div>
            <div>
              <dt className="label">סיסמה זמנית</dt>
              <dd className="field select-all font-mono text-lg" dir="ltr">
                {created.account.temporary_password}
              </dd>
            </div>
          </dl>
          <button
            type="button"
            className="btn-soft mt-4"
            onClick={() =>
              navigator.clipboard?.writeText(
                `${created.account!.email} / ${created.account!.temporary_password}`,
              )
            }
          >
            העתקת פרטי הכניסה
          </button>
        </div>
        <button
          className="btn-primary mt-6"
          onClick={() => navigate(`/patients/${created.id}`)}
        >
          המשך לתיק המטופל
        </button>
      </div>
    );
  }
  return (
    <div>
      <h1 className="text-3xl font-black">מטופל חדש</h1>
      <p className="mt-2 text-slate-500">
        תעודת הזהות מוצפנת ומוסתרת כברירת מחדל.
      </p>
      <form
        onSubmit={submit}
        className="card mt-6 grid max-w-3xl gap-5 p-6 sm:grid-cols-2"
      >
        {[
          ["first_name", "שם פרטי", "text"],
          ["last_name", "שם משפחה", "text"],
          ["national_id", "תעודת זהות", "text"],
          ["date_of_birth", "תאריך לידה", "date"],
          ["email", "דוא״ל", "email"],
          ["phone", "טלפון", "tel"],
        ].map(([name, label, type]) => (
          <label key={name}>
            <span className="label">{label}</span>
            <input
              className="field"
              name={name}
              type={type}
              required={!["email", "phone"].includes(name)}
            />
          </label>
        ))}
        <label>
          <span className="label">מין ביולוגי לצורך בחירת טווח</span>
          <select className="field" name="biological_sex" required>
            <option value="">בחירה</option>
            <option value="FEMALE">נקבה</option>
            <option value="MALE">זכר</option>
          </select>
        </label>
        {role === "ADMIN" && (
          <label>
            <span className="label">מרפאה מטפלת</span>
            <select className="field" name="clinic_id" required>
              <option value="">בחירה</option>
              {(clinics.data || []).map((clinic) => (
                <option key={clinic.id} value={clinic.id}>
                  {clinic.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="sm:col-span-2 flex items-start gap-3 rounded-xl bg-brand-50 p-4">
          <input type="checkbox" name="create_account" className="mt-1 h-4 w-4" />
          <span className="text-sm">
            <b>יצירת חשבון כניסה למטופל</b>
            <span className="block text-slate-600">
              המטופל יוכל להתחבר ולצפות בתוצאות שלו בלבד. נדרשת כתובת דוא״ל.
              הסיסמה תוצג פעם אחת בסיום.
            </span>
          </span>
        </label>
        {error && (
          <div
            role="alert"
            className="sm:col-span-2 rounded-xl bg-red-50 p-3 text-red-800"
          >
            {error}
          </div>
        )}
        <div className="sm:col-span-2">
          <button className="btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "שומר..." : "יצירת מטופל"}
          </button>
        </div>
      </form>
    </div>
  );
}
