import React, { useEffect, useMemo, useState } from "react";

const SCORES = [
  { value: "complete", label: "完整" },
  { value: "partial", label: "能答" },
  { value: "miss", label: "不会" },
];

const STORAGE_KEY = "ehs-practice-scores-v1";

function loadScores() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveScores(obj) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
}

export default function PracticePanel() {
  const [questions, setQuestions] = useState([]);
  const [scores, setScores] = useState(loadScores);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/practice-questions.json")
      .then((r) => {
        if (!r.ok) throw new Error("无法加载题库");
        return r.json();
      })
      .then(setQuestions)
      .catch((e) => setError(e.message));
  }, []);

  const sections = useMemo(() => {
    const s = new Set(questions.map((q) => q.section));
    return ["all", ...s];
  }, [questions]);

  const visible = questions.filter((q) => filter === "all" || q.section === filter);

  const tally = useMemo(() => {
    const t = { complete: 0, partial: 0, miss: 0, unset: 0 };
    for (const q of questions) {
      const v = scores[q.id];
      if (v === "complete" || v === "partial" || v === "miss") t[v] += 1;
      else t.unset += 1;
    }
    return t;
  }, [questions, scores]);

  const setScore = (id, value) => {
    const next = { ...scores, [id]: value };
    setScores(next);
    saveScores(next);
  };

  const reset = () => {
    setScores({});
    saveScores({});
  };

  return (
    <div className="panel">
      <div className="card">
        <h2>面试练习模式（Ch17）</h2>
        <p className="muted small">
          题库来自 practice-questions.json · 评分仅存 localStorage · 标准见 docs/practice-rubric.md
        </p>
        <div className="row gap" style={{ flexWrap: "wrap", marginBottom: 8 }}>
          {sections.map((s) => (
            <button
              key={s}
              type="button"
              className={filter === s ? "" : "ghost"}
              onClick={() => setFilter(s)}
            >
              {s === "all" ? "全部" : s}
            </button>
          ))}
          <button type="button" className="ghost" onClick={reset}>
            清空本地分
          </button>
        </div>
        <p className="small">
          完整 <strong>{tally.complete}</strong> · 能答 <strong>{tally.partial}</strong> · 不会{" "}
          <strong>{tally.miss}</strong> · 未评 <strong>{tally.unset}</strong>
        </p>
        {error && <p className="error">{error}</p>}
        <ul className="list practice-list">
          {visible.map((q) => (
            <li key={q.id} className="practice-item">
              <div className="row between">
                <span className="tag">{q.section}</span>
                <code className="muted small">{q.id}</code>
              </div>
              <div className="title">{q.question}</div>
              <div className="meta">要点：{(q.rubric_points || []).join(" · ")}</div>
              <div className="meta muted">指认：{q.hint_path}</div>
              <div className="row gap" style={{ marginTop: 6 }}>
                {SCORES.map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    className={scores[q.id] === s.value ? "" : "ghost"}
                    onClick={() => setScore(q.id, s.value)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
