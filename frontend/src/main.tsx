import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, ApiError, clearCsrf, message, User } from "./api";
import { Brand, ErrorNote } from "./components";
import { Auth } from "./Auth";
import { Tasks } from "./Tasks";
import "./styles.css";

function App() {
  const [route, setRoute] = useState(location.pathname);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [startupError, setStartupError] = useState("");
  const [notice, setNotice] = useState("");
  function navigate(path: string) {
    history.pushState({}, "", path);
    setRoute(location.pathname);
    setNotice(
      path.includes("registered=1")
        ? "Account created. Sign in to continue."
        : "",
    );
  }
  useEffect(() => {
    const pop = () => {
      setRoute(location.pathname);
      setNotice("");
    };
    const expired = () => {
      setUser(null);
      clearCsrf();
      history.replaceState({}, "", "/login");
      setRoute("/login");
      setNotice("Your session has expired. Please sign in again.");
    };
    window.addEventListener("popstate", pop);
    window.addEventListener("session-expired", expired);
    return () => {
      window.removeEventListener("popstate", pop);
      window.removeEventListener("session-expired", expired);
    };
  }, []);
  async function load() {
    setLoading(true);
    setStartupError("");
    try {
      const current = await api<User>("/auth/me", "GET", undefined, false);
      setUser(current);
      history.replaceState({}, "", "/tasks");
      setRoute("/tasks");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setNotice("");
        if (location.pathname !== "/register") {
          history.replaceState({}, "", "/login");
          setRoute("/login");
        }
      } else setStartupError(message(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  if (loading)
    return (
      <div className="startup" role="status">
        <Brand />
        <p>Getting things ready…</p>
      </div>
    );
  if (startupError)
    return (
      <main className="startup">
        <Brand />
        <ErrorNote>{startupError}</ErrorNote>
        <button onClick={load}>Try again</button>
      </main>
    );
  if (user)
    return (
      <Tasks
        user={user}
        onLogout={() => {
          setUser(null);
          navigate("/login");
        }}
      />
    );
  return (
    <Auth
      key={route}
      register={route === "/register"}
      navigate={navigate}
      notice={notice}
      onLogin={(current) => {
        setUser(current);
        navigate("/tasks");
      }}
    />
  );
}

createRoot(document.getElementById("root")!).render(<App />);
