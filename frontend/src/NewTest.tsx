import { FormEvent, useState } from "react";
import { Plus } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "./api";

type Row = {
  analyte_code: string;
  numeric_value: string;
  unit: string;
  reference_min: string;
  reference_max: string;
};
export default function NewTest() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [rows, setRows] = useState<Row[]>([
    {
      analyte_code: "HGB",
      numeric_value: "",
      unit: "g/dL",
      reference_min: "12",
      reference_max: "16",
    },
  ]);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    api
      .createTest({
        patient_id: id,
        laboratory_id: 1,
        test_date: data.get("test_date"),
        accession_number: data.get("accession_number"),
        panel: data.get("panel"),
        source: "MANUAL",
        results: rows.map((r) => ({
          ...r,
          numeric_value: Number(r.numeric_value),
          reference_min: r.reference_min ? Number(r.reference_min) : null,
          reference_max: r.reference_max ? Number(r.reference_max) : null,
          verified: true,
        })),
      })
      .then((result) => {
        queryClient.invalidateQueries({ queryKey: ["tests", id] });
        navigate(`/tests/${result.id}`);
      })
      .catch((e) => setError(e.message));
  };
  return (
    <div>
      <h1 className="text-3xl font-black">הזנת בדיקת דם</h1>
      <p className="mt-2 text-slate-500">
        כל ערך ינותח באופן דטרמיניסטי מול טווח הייחוס המתאים.
      </p>
      <form onSubmit={submit} className="mt-6 space-y-5">
        <div className="card grid gap-4 p-5 sm:grid-cols-3">
          <label>
            <span className="label">תאריך בדיקה</span>
            <input className="field" type="date" name="test_date" required />
          </label>
          <label>
            <span className="label">מספר בדיקה</span>
            <input className="field" name="accession_number" required />
          </label>
          <label>
            <span className="label">פאנל</span>
            <select className="field" name="panel">
              <option>CBC</option>
              <option>CHEMISTRY</option>
              <option>LIPIDS</option>
            </select>
          </label>
        </div>
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px] text-right">
            <thead className="bg-slate-50">
              <tr>
                <th className="p-3">בדיקה</th>
                <th>ערך</th>
                <th>יחידה</th>
                <th>מינימום</th>
                <th>מקסימום</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr className="border-t" key={index}>
                  {(
                    [
                      "analyte_code",
                      "numeric_value",
                      "unit",
                      "reference_min",
                      "reference_max",
                    ] as const
                  ).map((key) => (
                    <td className="p-2" key={key}>
                      <input
                        className="field"
                        value={row[key]}
                        onChange={(e) =>
                          setRows(
                            rows.map((current, i) =>
                              i === index
                                ? { ...current, [key]: e.target.value }
                                : current,
                            ),
                          )
                        }
                        required={[
                          "analyte_code",
                          "numeric_value",
                          "unit",
                        ].includes(key)}
                      />
                    </td>
                  ))}
                  <td>
                    <button
                      type="button"
                      className="btn-soft"
                      onClick={() =>
                        setRows(rows.filter((_, i) => i !== index))
                      }
                    >
                      הסרה
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t p-4">
            <button
              type="button"
              className="btn-soft"
              onClick={() =>
                setRows([
                  ...rows,
                  {
                    analyte_code: "WBC",
                    numeric_value: "",
                    unit: "10^3/uL",
                    reference_min: "4",
                    reference_max: "11",
                  },
                ])
              }
            >
              <Plus className="h-4 w-4" />
              הוספת מדד
            </button>
          </div>
        </div>
        {error && (
          <div role="alert" className="rounded-xl bg-red-50 p-3 text-red-800">
            {error}
          </div>
        )}
        <button className="btn-primary">שמירה וניתוח</button>
      </form>
    </div>
  );
}
