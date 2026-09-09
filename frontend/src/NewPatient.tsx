import { FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "./api";
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
  const mutation = useMutation({
    mutationFn: api.createPatient,
    onSuccess: (patient) => navigate(`/patients/${patient.id}`),
    onError: (e) => setError((e as Error).message),
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body: Record<string, unknown> = Object.fromEntries(
      new FormData(event.currentTarget).entries(),
    );
    if (body.clinic_id) body.clinic_id = Number(body.clinic_id);
    mutation.mutate(body);
  };
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
