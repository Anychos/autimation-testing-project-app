import React, { useState } from "react";
import { api, clearCsrf, fieldErrors, message, User } from "./api";
import { Brand, ErrorNote, FieldError } from "./components";

export function Auth({
  register,
  navigate,
  onLogin,
  notice,
}: {
  register: boolean;
  navigate: (path: string) => void;
  onLogin: (user: User) => void;
  notice: string;
}) {
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setErrors({});
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email")).trim();
    const password = String(data.get("password"));
    const invalid: Record<string, string> = {};
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      invalid.email = "Enter a valid email address.";
    if (Array.from(password).length < 8 || Array.from(password).length > 64)
      invalid.password = "Use 8–64 characters.";
    if (register && password !== data.get("confirmation"))
      invalid.confirmation = "Passwords do not match.";
    if (Object.keys(invalid).length) {
      setErrors(invalid);
      return;
    }
    setBusy(true);
    try {
      const user = await api<User>(
        register ? "/auth/register" : "/auth/login",
        "POST",
        { email, password },
      );
      clearCsrf();
      if (register) navigate("/login?registered=1");
      else onLogin(user);
    } catch (e) {
      setError(message(e));
      setErrors(fieldErrors(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-layout">
      <section className="auth-story">
        <Brand />
        <div>
          <h1>
            Make room for
            <br />
            what matters.
          </h1>
          <p>
            Your plans, your pace. Keep everything you need to do in one calm,
            simple space.
          </p>
          <div className="story-card">
            <span className="story-check">✓</span>
            <div>
              <strong>One thing at a time</strong>
              <small>Big plans start with a small next step.</small>
            </div>
          </div>
        </div>
      </section>
      <section className="auth-panel">
        <div className="auth-box">
          <h2>{register ? "Create your account" : "Welcome back"}</h2>
          <p className="muted">
            {register
              ? "A fresh start for your everyday plans."
              : "Let’s pick up where you left off."}
          </p>
          {notice && (
            <p role="status" className="notice">
              {notice}
            </p>
          )}
          {error && <ErrorNote>{error}</ErrorNote>}
          <form
            onSubmit={submit}
            noValidate
            data-testid={register ? "register-form" : "login-form"}
          >
            <label htmlFor="email">Email</label>
            <input
              autoFocus
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              data-testid="email-input"
              aria-invalid={!!errors.email}
              aria-describedby="email-error"
            />
            <FieldError name="email" errors={errors} />
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              placeholder="8–64 characters"
              data-testid="password-input"
              aria-invalid={!!errors.password}
              aria-describedby="password-error"
            />
            <FieldError name="password" errors={errors} />
            {register && (
              <>
                <label htmlFor="confirmation">Confirm password</label>
                <input
                  id="confirmation"
                  name="confirmation"
                  type="password"
                  autoComplete="new-password"
                  data-testid="confirm-password-input"
                  aria-invalid={!!errors.confirmation}
                  aria-describedby="confirmation-error"
                />
                <FieldError name="confirmation" errors={errors} />
              </>
            )}
            <button
              className="primary full"
              disabled={busy}
              data-testid="auth-submit"
            >
              {busy ? "Please wait…" : register ? "Create account" : "Sign in"}
              <span aria-hidden="true"> →</span>
            </button>
          </form>
          <p className="auth-switch">
            {register ? "Already have an account?" : "New to TaskFlow?"}{" "}
            <a
              href={register ? "/login" : "/register"}
              data-testid="auth-switch"
              onClick={(e) => {
                e.preventDefault();
                navigate(register ? "/login" : "/register");
              }}
            >
              {register ? "Sign in" : "Create an account"}
            </a>
          </p>
        </div>
      </section>
    </main>
  );
}
