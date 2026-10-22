import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001/api",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("erp-token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes("/auth/login")) {
      localStorage.removeItem("erp-token");
      window.dispatchEvent(new Event("erp:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export default api;
