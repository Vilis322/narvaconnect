import { useEffect, useState } from "react";

type Deadline = {
  subject_code: string;
  subject_name: string;
  date: string;
  type: string;
  description: string | null;
};

function daysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  const diff = target.getTime() - today.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export default function Deadlines() {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);

  useEffect(() => {
    fetch("/api/deadlines")
      .then((r) => r.json())
      .then(setDeadlines);
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-white">Upcoming Deadlines</h2>
      {deadlines.length === 0 && (
        <p className="text-slate-400">No upcoming deadlines.</p>
      )}
      {deadlines.map((d, i) => {
        const days = daysUntil(d.date);
        const urgency =
          days <= 2
            ? "border-red-500 bg-red-950/30"
            : days <= 7
            ? "border-yellow-500 bg-yellow-950/30"
            : "border-slate-700 bg-slate-800";
        return (
          <div key={i} className={`border rounded-lg p-4 ${urgency}`}>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-white">{d.subject_name}</span>
              <span className="text-xs font-bold text-white">
                {days === 0 ? "TODAY" : days < 0 ? "past" : `in ${days}d`}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
              <span className="bg-slate-700 px-2 py-0.5 rounded uppercase">
                {d.type}
              </span>
              <span>{d.date}</span>
              <span>{d.subject_code}</span>
            </div>
            {d.description && (
              <p className="text-sm text-slate-300 mt-2">{d.description}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
