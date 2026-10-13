import { useCallback, useEffect, useState } from "react";
import DomainPanel from "./components/DomainPanel.jsx";
import { advanceTicket, createTicket, fetchSummary } from "./api/domain.js";

export default function App() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchSummary();
      setSummary(data);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function onCreate(payload) {
    setLoading(true);
    setError("");
    try {
      await createTicket(payload);
      await refresh();
    } catch (e) {
      setError(e.message || String(e));
      setLoading(false);
    }
  }

  async function onAdvance(ticketId, payload) {
    setLoading(true);
    setError("");
    try {
      await advanceTicket(ticketId, payload);
      await refresh();
    } catch (e) {
      setError(e.message || String(e));
      setLoading(false);
    }
  }

  return (
    <DomainPanel
      summary={summary}
      loading={loading}
      error={error}
      onRefresh={refresh}
      onCreate={onCreate}
      onAdvance={onAdvance}
    />
  );
}
