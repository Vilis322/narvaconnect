import { useEffect, useState } from "react";

type Event = {
  subject_code: string;
  subject_name: string;
  date: string;
  time_start: string | null;
  time_end: string | null;
  type: string;
  description: string | null;
  room: string | null;
};

export default function Schedule() {
  const [events, setEvents] = useState<Event[]>([]);

  useEffect(() => {
    fetch("/api/schedule")
      .then((r) => r.json())
      .then(setEvents);
  }, []);

  // Group by date
  const byDate: Record<string, Event[]> = {};
  for (const e of events) {
    if (!byDate[e.date]) byDate[e.date] = [];
    byDate[e.date].push(e);
  }

  const dates = Object.keys(byDate).sort();

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Schedule</h2>
      {dates.length === 0 && (
        <p className="text-slate-400">Loading schedule...</p>
      )}
      {dates.map((date) => (
        <div key={date}>
          <h3 className="text-sm font-semibold text-blue-400 mb-2">{date}</h3>
          <div className="space-y-2">
            {byDate[date].map((e, i) => (
              <div
                key={i}
                className="bg-slate-800 border border-slate-700 rounded-lg p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-white">
                    {e.subject_name}
                  </span>
                  <span className="text-xs text-slate-400">
                    {e.time_start}
                    {e.time_end ? `–${e.time_end}` : ""}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                  <span className="bg-slate-700 px-2 py-0.5 rounded">
                    {e.type}
                  </span>
                  <span>{e.subject_code}</span>
                  {e.room && <span>• {e.room}</span>}
                </div>
                {e.description && (
                  <p className="text-sm text-slate-300 mt-2">{e.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
