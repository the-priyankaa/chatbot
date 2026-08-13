import { createContext, useCallback, useContext, useEffect, useState } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const handleAuthExpired = useCallback(() => setUser(null), []);

  useEffect(() => {
    window.addEventListener("auth-expired", handleAuthExpired);
    return () => window.removeEventListener("auth-expired", handleAuthExpired);
  }, [handleAuthExpired]);

  const fetchMe = useCallback(async () => {
    try {
      const { data } = await client.get("/auth/me");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (localStorage.getItem("access_token")) fetchMe();
    else setLoading(false);
  }, [fetchMe]);

  const login = async (identifier, password) => {
    const { data } = await client.post("/auth/login", { identifier, password });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    await fetchMe();
  };

  const register = async (username, email, password) => {
    const { data } = await client.post("/auth/register", {
      username,
      email,
      password,
    });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    await fetchMe();
  };

  const logout = async () => {
    try {
      await client.post("/auth/logout", {
        refresh_token: localStorage.getItem("refresh_token"),
      });
    } catch {
      /* ignore */
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
