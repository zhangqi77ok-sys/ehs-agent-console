import { useState } from "react";
import ChatPanel from "./components/ChatPanel.jsx";
import StepsPanel from "./components/StepsPanel.jsx";
import { chat } from "./api/chat.js";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [steps, setSteps] = useState([]);
  const [budget, setBudget] = useState({ used: 0, max: 8, unit: "steps" });
  const [loading, setLoading] = useState(false);

  async function onSend(text) {
    const history = messages
      .filter((m) => !m.error)
      .map((m) => ({ role: m.role === "assistant" ? "assistant" : "user", content: m.content }));

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setSteps([]);
    try {
      const data = await chat(text, history);
      setSteps(data.steps || []);
      setBudget(data.budget || { used: 0, max: 8, unit: "steps" });
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `请求失败：${err.message}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>EHS 隐患闭环 Agent 控制台</h1>
        <span className="meta">MVP · 默认 Mock LLM · FastAPI + React</span>
      </header>
      <div className="main">
        <ChatPanel messages={messages} loading={loading} onSend={onSend} />
        <StepsPanel steps={steps} budget={budget} />
      </div>
    </div>
  );
}
