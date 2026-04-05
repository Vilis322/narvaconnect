import { useState, useRef, useEffect } from "react";

type Msg = { role: "user" | "assistant"; content: string };

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!input.trim() || loading) return;

    const question = input;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: question }]);
    setMessages((m) => [...m, { role: "assistant", content: "" }]);
    setLoading(true);

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      const reader = resp.body?.getReader();
      const decoder = new TextDecoder();

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        for (const line of chunk.split("\n")) {
          if (line.startsWith("data: ")) {
            try {
              const obj = JSON.parse(line.slice(6));
              if (obj.token) {
                setMessages((m) => {
                  const updated = [...m];
                  updated[updated.length - 1].content += obj.token;
                  return updated;
                });
              }
              if (obj.done) break;
            } catch {}
          }
        }
      }
    } catch (e: any) {
      setMessages((m) => {
        const updated = [...m];
        updated[updated.length - 1].content = `Error: ${e.message}`;
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-2xl font-bold text-white mb-4">AI Assistant</h2>

      <div className="flex-1 overflow-auto space-y-3 mb-4">
        {messages.length === 0 && (
          <p className="text-slate-400 text-sm">
            Ask me anything about your schedule, teachers, or subjects...
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-lg p-3 ${
              m.role === "user"
                ? "bg-blue-900/40 border border-blue-800 ml-12"
                : "bg-slate-800 border border-slate-700 mr-12"
            }`}
          >
            <div className="text-xs text-slate-400 mb-1">
              {m.role === "user" ? "You" : "NarvaConnect AI"}
            </div>
            <div className="text-sm text-slate-100 whitespace-pre-wrap">
              {m.content}
              {loading && i === messages.length - 1 && (
                <span className="inline-block w-2 h-4 bg-blue-400 ml-1 animate-pulse" />
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Who teaches Data Science?"
          disabled={loading}
          className="flex-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 text-white px-4 py-2 rounded text-sm font-medium"
        >
          Send
        </button>
      </div>
    </div>
  );
}
