import { useEffect, useState, useRef } from "react";

type LogLine = { timestamp: string; message: string };

export default function LogStream() {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://${window.location.hostname}:3000/ws/logs`
    );
    ws.onmessage = (e) => {
      try {
        const line: LogLine = JSON.parse(e.data);
        setLogs((prev) => [...prev.slice(-100), line]);
      } catch {}
    };
    ws.onerror = () => {
      setLogs((prev) => [
        ...prev,
        { timestamp: "--:--:--", message: "[WS] connection error" },
      ]);
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="flex-1 overflow-auto p-3 font-mono text-xs">
      {logs.length === 0 && (
        <p className="text-slate-500">Waiting for server activity...</p>
      )}
      {logs.map((line, i) => (
        <div key={i} className="mb-1">
          <span className="text-slate-500">[{line.timestamp}]</span>{" "}
          <span className="text-green-400">{line.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
