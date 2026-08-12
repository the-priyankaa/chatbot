import axios from "axios";

const client = axios.create({ baseURL: "/api" });

let refreshPromise = null;

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        localStorage.clear();
        window.dispatchEvent(new Event("auth-expired"));
        return Promise.reject(error);
      }
      try {
        refreshPromise =
          refreshPromise ||
          axios.post("/api/auth/refresh", { refresh_token: refreshToken });
        const { data } = await refreshPromise;
        refreshPromise = null;
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return client(original);
      } catch (refreshError) {
        refreshPromise = null;
        localStorage.clear();
        window.dispatchEvent(new Event("auth-expired"));
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default client;
