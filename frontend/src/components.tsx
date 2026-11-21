import React from "react";
import { Status } from "./api";

export const labels: Record<Status, string> = {
  todo: "To do",
  in_progress: "In progress",
  done: "Completed",
};
export function Brand() {
  return (
    <span className="brand">
      <span className="brand-icon" aria-hidden="true">
        ✓
      </span>
      TaskFlow<span className="brand-dot">.</span>
    </span>
  );
}
export function ErrorNote({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="error-note">
      {children}
    </p>
  );
}
export function FieldError({
  name,
  errors,
}: {
  name: string;
  errors: Record<string, string>;
}) {
  return errors[name] ? (
    <span id={`${name}-error`} className="field-error" role="alert">
      {errors[name]}
    </span>
  ) : null;
}
