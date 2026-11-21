import React, { useEffect, useRef, useState } from "react";
import { api, fieldErrors, message, Task, TaskBody, Status } from "./api";
import { ErrorNote, FieldError, labels } from "./components";

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current!;
    el.showModal();
    return () => el.close();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      aria-labelledby="dialog-title"
      data-testid="task-dialog"
    >
      <div className="dialog-heading">
        <h2 id="dialog-title">{title}</h2>
        <button
          type="button"
          className="icon-button"
          onClick={onClose}
          aria-label="Close dialog"
        >
          ×
        </button>
      </div>
      {children}
    </dialog>
  );
}

export function TaskForm({
  task,
  onClose,
  onSaved,
}: {
  task: Task | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setErrors({});
    const data = new FormData(e.currentTarget);
    const body: TaskBody = {
      title: String(data.get("title")).trim(),
      description: String(data.get("description")),
      status: data.get("status") as Status,
      due_date: String(data.get("due_date")) || null,
    };
    const invalid: Record<string, string> = {};
    if (
      Array.from(body.title).length < 3 ||
      Array.from(body.title).length > 100
    )
      invalid.title = "Use 3–100 characters after trimming spaces.";
    if (Array.from(body.description).length > 500)
      invalid.description = "Use at most 500 characters.";
    if (Object.keys(invalid).length) {
      setErrors(invalid);
      return;
    }
    setBusy(true);
    try {
      await api(
        task ? `/tasks/${task.id}` : "/tasks",
        task ? "PATCH" : "POST",
        body,
      );
      onSaved();
    } catch (e) {
      setErrors(fieldErrors(e));
      setError(message(e));
      setBusy(false);
    }
  }
  return (
    <Modal
      title={task ? "Edit task" : "Create task"}
      onClose={() => !busy && onClose()}
    >
      <p className="muted">A clear next step makes all the difference.</p>
      {error && <ErrorNote>{error}</ErrorNote>}
      <form onSubmit={save} noValidate data-testid="task-form">
        <fieldset disabled={busy}>
          <label htmlFor="title">
            Title <span className="muted">*</span>
          </label>
          <input
            autoFocus
            id="title"
            name="title"
            defaultValue={task?.title || ""}
            placeholder="What would you like to get done?"
            data-testid="task-title-input"
            aria-invalid={!!errors.title}
            aria-describedby="title-error"
          />
          <FieldError name="title" errors={errors} />
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            rows={4}
            defaultValue={task?.description || ""}
            placeholder="Add a few details (optional)"
            data-testid="task-description-input"
            aria-invalid={!!errors.description}
            aria-describedby="description-error"
          />
          <FieldError name="description" errors={errors} />
          <div className="form-row">
            <div>
              <label htmlFor="status">Status</label>
              <select
                id="status"
                name="status"
                defaultValue={task?.status || "todo"}
                data-testid="task-status-input"
              >
                {Object.entries(labels).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
              <FieldError name="status" errors={errors} />
            </div>
            <div>
              <label htmlFor="due_date">Due date</label>
              <input
                id="due_date"
                name="due_date"
                type="date"
                defaultValue={task?.due_date || ""}
                data-testid="task-due-date-input"
                aria-invalid={!!errors.due_date}
                aria-describedby="due_date-error"
              />
              <FieldError name="due_date" errors={errors} />
            </div>
          </div>
          <div className="dialog-actions">
            <button type="button" onClick={onClose} data-testid="task-cancel">
              Cancel
            </button>
            <button className="primary" data-testid="task-save">
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}

export function DeleteTask({
  task,
  onClose,
  onDeleted,
}: {
  task: Task;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function remove() {
    setBusy(true);
    setError("");
    try {
      await api(`/tasks/${task.id}`, "DELETE");
      onDeleted();
    } catch (e) {
      setError(message(e));
      setBusy(false);
    }
  }
  return (
    <Modal title="Delete task?" onClose={() => !busy && onClose()}>
      <p className="muted">“{task.title}” will be permanently deleted.</p>
      {error && <ErrorNote>{error}</ErrorNote>}
      <div className="dialog-actions">
        <button onClick={onClose} disabled={busy} data-testid="delete-cancel">
          Cancel
        </button>
        <button
          className="danger"
          onClick={remove}
          disabled={busy}
          data-testid="delete-confirm"
        >
          {busy ? "Deleting…" : "Confirm"}
        </button>
      </div>
    </Modal>
  );
}
