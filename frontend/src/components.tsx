import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  FlaskConical,
  Info,
  ShieldCheck,
} from "lucide-react";
export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3" aria-label="HEMORA">
      <svg
        viewBox="0 0 48 56"
        className={compact ? "h-9 w-8" : "h-12 w-10"}
        role="img"
        aria-label="סמל HEMORA"
      >
        <path
          d="M24 2C18 12 7 23 7 36a17 17 0 0 0 34 0C41 23 30 12 24 2Z"
          fill="#0d746f"
        />
        <path
          d="M12 36h7l3-8 5 16 4-10h6"
          fill="none"
          stroke="#fff"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div>
        <div className="text-xl font-black tracking-[.16em] text-ink">
          HEMORA
        </div>
        {!compact && (
          <div className="text-xs text-slate-500" dir="ltr">
            Understanding change. Protecting health.
          </div>
        )}
      </div>
    </div>
  );
}
const statusText: Record<string, string> = {
  NORMAL: "בטווח",
  LOW: "נמוך",
  HIGH: "גבוה",
  CRITICAL_LOW: "קריטי נמוך",
  CRITICAL_HIGH: "קריטי גבוה",
  UNVERIFIED: "דורש אימות",
  UNKNOWN_REFERENCE: "ללא טווח ייחוס",
  INVALID: "לא תקין",
};
export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge status-${status}`}>
      {statusText[status] || status}
    </span>
  );
}
export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="card p-10 text-center">
      <FlaskConical className="mx-auto mb-3 text-slate-400" />
      <h3 className="font-bold">{title}</h3>
      <p className="mt-2 text-sm text-slate-500">{body}</p>
    </div>
  );
}
export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="card border-red-200 p-6">
      <div className="flex items-center gap-2 font-bold text-red-800">
        <AlertTriangle />
        לא הצלחנו להשלים את הפעולה
      </div>
      <p className="mt-2 text-sm text-slate-600">{message}</p>
      {onRetry && (
        <button className="btn-soft mt-4" onClick={onRetry}>
          נסו שוב
        </button>
      )}
    </div>
  );
}
export function Disclaimer() {
  return (
    <footer className="border-t border-slate-200 bg-white p-4 text-center text-xs leading-6 text-slate-500">
      <ShieldCheck className="mx-1 inline h-4 w-4" />
      HEMORA היא מערכת תומכת מידע ואינה מהווה אבחנה רפואית, ייעוץ רפואי או תחליף
      לבדיקה ולהחלטה של איש מקצוע רפואי. טווחי ייחוס עשויים להשתנות בין מעבדות
      ובין מטופלים.
    </footer>
  );
}
export function Skeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-24 rounded-2xl bg-slate-200" />
      <div className="h-52 rounded-2xl bg-slate-200" />
    </div>
  );
}
export function SourceNotice({ source }: { source: string }) {
  if (source === "DEMO_GENERAL")
    return (
      <div className="mt-2 flex gap-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-900">
        <Info className="h-4 w-4 shrink-0" />
        הטווח המוצג הוא טווח ייחוס כללי למטרות מידע בלבד. יש להעדיף את טווח
        הייחוס שסופק על ידי המעבדה המבצעת.
      </div>
    );
  return (
    <span className="text-xs text-slate-500">
      מקור הטווח:{" "}
      {source === "LAB_SUPPLIED" ? "סופק על ידי המעבדה" : "הגדרת מעבדה"}
    </span>
  );
}
export function TrendLabel({ trend }: { trend: string }) {
  const map: Record<string, string> = {
    IMPROVED: "השתפר אך עדיין חריג",
    WORSENED: "התרחק מהטווח",
    STABLE: "יציב",
    NEW_ABNORMALITY: "חריגה חדשה",
    RETURNED_TO_RANGE: "חזר לטווח",
    STILL_ABNORMAL: "עדיין חריג",
    NEW_PARAMETER: "מדד חדש",
    MISSING_CURRENT: "חסר בבדיקה הנוכחית",
    NOT_COMPARABLE: "לא ניתן להשוואה",
  };
  return (
    <span className="inline-flex items-center gap-1 text-sm font-semibold">
      <CheckCircle2 className="h-4 w-4 text-brand-600" />
      {map[trend] || trend}
    </span>
  );
}
export { ChevronLeft };
