import { useState } from "react";
import Schedule from "./components/Schedule";
import Deadlines from "./components/Deadlines";
import Chat from "./components/Chat";
import LogStream from "./components/LogStream";

type Tab = "schedule" | "deadlines" | "chat";

export default function App() {
  const [tab, setTab] = useState<Tab>("schedule");

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-700 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">NarvaConnect</h1>
          <p className="text-xs text-slate-400">
            Narva Kolledž — Spring 2026 — Kyrylo Pryiomyshev
          </p>
        </div>
        <nav className="flex gap-2">
          {(["schedule", "deadlines", "chat"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded text-sm font-medium transition ${
                tab === t
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
      </header>

      {/* Main */}
      <main className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-auto p-6">
          {tab === "schedule" && <Schedule />}
          {tab === "deadlines" && <Deadlines />}
          {tab === "chat" && <Chat />}
        </div>

        {/* Log stream sidebar */}
        <aside className="w-96 border-l border-slate-700 bg-slate-950 overflow-hidden flex flex-col">
          <div className="border-b border-slate-700 px-4 py-2">
            <h3 className="text-sm font-semibold text-slate-300">
              Server Logs (live)
            </h3>
          </div>
          <LogStream />
        </aside>
      </main>
    </div>
  );
}
