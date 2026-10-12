import { useState } from "react";
import ChatPanel from "./components/ChatPanel.jsx";
import StepsPanel from "./components/StepsPanel.jsx";
import { chatStream } from "./api/chat.js";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [steps, setSteps] = useState([]);
  const [budget, setBudget] = useState({ used: 0, max: 8, unit: "steps" });
  const [loading, setLoading] = useState(false);
  const [streamingHint, setStreamingHint] = useState("");

  async function onSend(text) {
    const history = messages
      .filter((m) => !m.error)
      .map((m) => ({
        role: m.role === "assistant" ? "assistant" : "user",
        content: m.content,
      }));

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setSteps([]);
    setBudget({ used: 0, max: 8, unit: "steps" });
    setStreamingHint("连接中…");

    try {
      const data = await chatStream(text, history, (eventName, payload) => {
        if (eventName === "step_start") {
          setStreamingHint(`第 ${payload.index} 步决策中…`);
        } else if (eventName === "tool_call") {
          setStreamingHint(`调用工具 ${payload.name}…`);
          setSteps((prev) => [...prev, payload]);
        } else if (eventName === "tool_result") {
          setStreamingHint(`工具 ${payload.name} 返回`);
          setSteps((prev) => [...prev, payload]);
        } else if (eventName === "final") {
          setStreamingHint("生成最终回答…");
          setSteps((prev) => [...prev, payload]);
        } else if (eventName === "budget") {
          setBudget(payload);
        }
      });

      setBudget(data.budget || { used: 0, max: 8, unit: "steps" });
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `请求失败：${err.message}`, error: true },
      ]);
    } finally {
      setLoading(false);
      setStreamingHint("");
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>EHS 隐患闭环 Agent 控制台</h1>
        <span className="meta">MVP · 真实 LLM · SSE 流式步骤 · FastAPI + React</span>
      </header>
      <div className="main">
        <ChatPanel
          messages={messages}
          loading={loading}
          streamingHint={streamingHint}
          onSend={onSend}
        />
        <StepsPanel steps={steps} budget={budget} streaming={loading} />
      </div>
    </div>
  );
}
