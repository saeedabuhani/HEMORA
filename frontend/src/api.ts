const base = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
export type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  masked_national_id: string;
  date_of_birth: string;
  biological_sex: string;
  demo: boolean;
  clinic_id: number | null;
  clinic_name: string | null;
  test_count: number;
  last_test_date: string | null;
};
export type TestSummary = {
  id: string;
  test_date: string;
  accession_number: string;
  panel: string;
  status: string;
  results_count: number;
};
export type TestResult = {
  id: number;
  code: string;
  name_he: string;
  description_he: string;
  value: number;
  unit: string;
  normalized_value: number | null;
  normalized_unit: string | null;
  reference_min: number | null;
  reference_max: number | null;
  reference_source: string;
  status: string;
  quality: string;
};
export type Explanation = {
  analyte: { code: string; name_he: string; description_he: string };
  measured: { value: number; unit: string; normalized_value: number | null; normalized_unit: string | null };
  reference: {
    min: number | null; max: number | null; source: string; source_he: string;
    critical_low: number | null; critical_high: number | null;
  };
  status: string;
  status_he: string;
  classification_reason: string;
  test_date: string;
  comparison: {
    previous_value?: number; previous_unit?: string; previous_date?: string;
    previous_status?: string; delta?: number; percent_delta?: number | null;
    days_between?: number; trend: string; trend_he: string;
    reliability?: string; rule_he: string;
  } | null;
  data_quality: string;
  limitations: string[];
  algorithm_version: string;
};
export type NewPatientResult = Patient & {
  account?: { email: string; temporary_password: string; notice: string };
};
export type Clinic = { id: number; name: string; code: string; city: string | null };
export type AssignedDoctor = { doctor_user_id: number; email: string; assigned_at: string };
export type TestDetail = {
  id: string;
  patient_id: string;
  test_date: string;
  accession_number: string;
  panel: string;
  source: string;
  results: TestResult[];
};
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem("access_token");
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");
  const response = await fetch(base + path, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      error.detail?.message || error.message || "אירעה שגיאה בתקשורת עם השרת",
      response.status,
    );
  }
  return response.json();
}
async function download(path: string, filename: string) {
  const token = sessionStorage.getItem("access_token");
  const response = await fetch(base + path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "הורדת הדוח נכשלה");
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
export const api = {
  config: (resource: string) => request<Record<string, any>[]>(`/admin/${resource}`),
  saveConfig: (resource: string, body: Record<string, any>, id?: number) => request(`/admin/${resource}${id ? `/${id}` : ""}`, {method:id ? "PUT" : "POST",body:JSON.stringify(body)}),
  alerts: () => request<{id:number;title_he:string;state:string;test_id:string}[]>("/alerts"),
  setAlert: (id:number,state:string) => request(`/alerts/${id}`,{method:"PATCH",body:JSON.stringify({state})}),
  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string; role: string }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
    ),
  patients: (search = "") =>
    request<{ items: Patient[]; total: number }>(
      `/patients?search=${encodeURIComponent(search)}`,
    ),
  patient: (id: string) => request<Patient>(`/patients/${id}`),
  tests: (id: string) => request<TestSummary[]>(`/patients/${id}/tests`),
  test: (id: string) => request<TestDetail>(`/tests/${id}`),
  analysis: (id: string) => request<any>(`/tests/${id}/analysis`),
  comparison: (id: string) => request<any>(`/tests/${id}/comparison`),
  trends: (id: string, code = "HGB") =>
    request<any>(`/patients/${id}/trends?code=${code}`),
  explanation: (testId: string, resultId: number) =>
    request<Explanation>(`/tests/${testId}/results/${resultId}/explanation`),
  summary: () =>
    request<{
      patients: number; tests: number; open_alerts: number; abnormal_results: number;
      average_quality: number | null; quality_note: string;
    }>("/summary"),
  clinics: () => request<Clinic[]>("/clinics"),
  deletePatient: (id: string) =>
    request<{ deleted: boolean; tests_removed: number }>(`/patients/${id}`, { method: "DELETE" }),
  createUser: (body: {
    email: string; password: string; role: string;
    clinic_id?: number | null; patient_id?: string | null;
  }) => request<{ id: number; email: string; role: string }>("/admin/users", {
    method: "POST", body: JSON.stringify(body),
  }),
  patientDoctors: (id: string) => request<AssignedDoctor[]>(`/patients/${id}/doctors`),
  assignDoctor: (id: string, doctorUserId: number) =>
    request(`/patients/${id}/doctors`, { method: "POST", body: JSON.stringify({ doctor_user_id: doctorUserId }) }),
  unassignDoctor: (id: string, doctorUserId: number) =>
    request(`/patients/${id}/doctors/${doctorUserId}`, { method: "DELETE" }),
  users: () => request<{ id: number; email: string; role: string; clinic_id: number | null }[]>("/admin/users"),
  analytes: () => request<any[]>("/analytes"),
  audit: () => request<any[]>("/audit"),
  createTest: (body: any) =>
    request<any>("/tests", { method: "POST", body: JSON.stringify(body) }),
  createPatient: (body: any) =>
    request<NewPatientResult>("/patients", { method: "POST", body: JSON.stringify(body) }),
  downloadReport: (id: string, format: "pdf" | "csv") =>
    download(`/reports/${id}.${format}`, `hemora-${id}.${format}`),
};
