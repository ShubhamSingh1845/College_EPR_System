import { useCallback, useEffect, useState } from "react";
import api from "../services/api";

export function useDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/dashboard");
      setData(response.data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    window.addEventListener("erp:refresh", refresh);
    return () => window.removeEventListener("erp:refresh", refresh);
  }, [refresh]);
  return { data, loading, error, refresh };
}
