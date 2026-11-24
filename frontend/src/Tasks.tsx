import React, { useEffect, useState } from "react";
import { api, ApiError, clearCsrf, message, Task, TaskList, User } from "./api";
import { Brand, ErrorNote, labels } from "./components";
import { TaskForm, DeleteTask } from "./TaskDialogs";

export function Tasks({
  user,
  onLogout,
}: {
  user: User;
  onLogout: () => void;
}) {
  const [data, setData] = useState<TaskList | null>(null);
  const [counts, setCounts] = useState({ total: 0, progress: 0, done: 0 });
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("created_desc");
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editor, setEditor] = useState<Task | null | undefined>(undefined);
  const [deleting, setDeleting] = useState<Task | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    let active = true;
    setBusy(true);
    setError("");
    const params = new URLSearchParams({
      sort,
      page: String(page),
      limit: String(limit),
    });
    if (status) params.set("status", status);
    if (search) params.set("q", search);
    Promise.all([
      api<TaskList>(`/tasks?${params}`),
      api<TaskList>("/tasks?limit=1"),
      api<TaskList>("/tasks?status=in_progress&limit=1"),
      api<TaskList>("/tasks?status=done&limit=1"),
    ])
      .then(([list, all, progress, done]) => {
        if (!active) return;
        if (page > 1 && page > list.pagination.pages) {
          setPage(Math.max(1, list.pagination.pages));
          return;
        }
        setData(list);
        setCounts({
          total: all.pagination.total,
          progress: progress.pagination.total,
          done: done.pagination.total,
        });
      })
      .catch((e) => {
        if (active) setError(message(e));
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [search, status, sort, page, limit, revision]);
  async function logout() {
    setLoggingOut(true);
    try {
      await api("/auth/logout", "POST");
      clearCsrf();
      onLogout();
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 401)) setError(message(e));
    } finally {
      setLoggingOut(false);
    }
  }
  function refreshed(text: string) {
    setEditor(undefined);
    setDeleting(null);
    setRevision((r) => r + 1);
    setNotice(text);
  }
  const filtered = !!search || !!status;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <span className="sidebar-label">WORKSPACE</span>
        <a href="/tasks" aria-current="page" className="nav-active">
          <span aria-hidden="true">▤</span> My Tasks{" "}
          <span className="nav-count">{counts.total}</span>
        </a>
        <div className="sidebar-footer">
          <strong>A little progress, every day.</strong>
          <p>Keep it simple. Keep moving.</p>
        </div>
      </aside>
      <div className="app-content">
        <header className="topbar">
          <span className="breadcrumb">
            Workspace <span>/</span> <strong>My Tasks</strong>
          </span>
          <div className="account">
            <span className="avatar" aria-hidden="true">
              {user.email[0].toUpperCase()}
            </span>
            <span className="user-email" data-testid="current-user-email">
              {user.email}
            </span>
            <button
              onClick={logout}
              disabled={loggingOut}
              className="logout"
              data-testid="logout-button"
            >
              {loggingOut ? "Leaving…" : "Logout"}
            </button>
          </div>
        </header>
        <main className="dashboard">
          <div className="page-heading">
            <div>
              <h1>
                My Tasks<span className="heading-dot">.</span>
              </h1>
              <p className="muted">
                A clear view of what’s next. Let’s make progress.
              </p>
            </div>
            <button
              className="primary"
              onClick={() => {
                setNotice("");
                setEditor(null);
              }}
              data-testid="create-task-button"
            >
              <span aria-hidden="true">＋</span> Create Task
            </button>
          </div>
          <section className="stats" aria-label="Task statistics">
            <div className="stat">
              <span className="stat-symbol total-symbol" aria-hidden="true">
                ▤
              </span>
              <div>
                <span>Total tasks</span>
                <strong data-testid="total-count">{counts.total}</strong>
              </div>
            </div>
            <div className="stat">
              <span className="stat-symbol progress-symbol" aria-hidden="true">
                ◷
              </span>
              <div>
                <span>In Progress</span>
                <strong data-testid="in-progress-count">
                  {counts.progress}
                </strong>
              </div>
            </div>
            <div className="stat">
              <span className="stat-symbol done-symbol" aria-hidden="true">
                ✓
              </span>
              <div>
                <span>Completed</span>
                <strong data-testid="completed-count">{counts.done}</strong>
              </div>
            </div>
          </section>
          <section className="task-section" aria-label="Your tasks">
            <div className="list-heading">
              <h2>
                All tasks{" "}
                <span className="pill">{data?.pagination.total ?? "—"}</span>
              </h2>
            </div>
            <div className="toolbar">
              <div className="search-field">
                <span aria-hidden="true">⌕</span>
                <input
                  aria-label="Search tasks"
                  placeholder="Search tasks…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  data-testid="task-search"
                  type="search"
                />
              </div>
              <div>
                <label className="sr-only" htmlFor="filter">
                  Filter by status
                </label>
                <select
                  id="filter"
                  value={status}
                  onChange={(e) => {
                    setStatus(e.target.value);
                    setPage(1);
                  }}
                  data-testid="status-filter"
                >
                  <option value="">All statuses</option>
                  {Object.entries(labels).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="sr-only" htmlFor="sort">
                  Sort tasks
                </label>
                <select
                  id="sort"
                  value={sort}
                  onChange={(e) => {
                    setSort(e.target.value);
                    setPage(1);
                  }}
                  data-testid="sort-select"
                >
                  <option value="created_desc">Newest first</option>
                  <option value="created_asc">Oldest first</option>
                  <option value="due_date_asc">Due date first</option>
                </select>
              </div>
            </div>
            {notice && (
              <p role="status" className="success-note">
                {notice}
              </p>
            )}
            {error ? (
              <div className="empty-state">
                <ErrorNote>{error}</ErrorNote>
                <button
                  onClick={() => setRevision((r) => r + 1)}
                  data-testid="retry-button"
                >
                  Try again
                </button>
              </div>
            ) : busy ? (
              <div
                className="empty-state"
                role="status"
                data-testid="tasks-loading"
              >
                <span className="loading-dot" />
                Loading your tasks…
              </div>
            ) : !data?.items.length ? (
              <div
                className="empty-state"
                data-testid={filtered ? "no-results" : "empty-tasks"}
              >
                <span className="empty-icon" aria-hidden="true">
                  {filtered ? "⌕" : "✓"}
                </span>
                <h3>
                  {filtered ? "No matching tasks" : "A fresh start awaits"}
                </h3>
                <p>
                  {filtered
                    ? "Try another search or change your filters."
                    : "Create your first task and take the next step."}
                </p>
                {filtered ? (
                  <button
                    onClick={() => {
                      setQuery("");
                      setSearch("");
                      setStatus("");
                      setPage(1);
                    }}
                  >
                    Clear filters
                  </button>
                ) : (
                  <button className="primary" onClick={() => setEditor(null)}>
                    Create Task
                  </button>
                )}
              </div>
            ) : (
              <div className="task-list" data-testid="task-list">
                {data.items.map((task) => (
                  <article
                    className={`task-card ${task.status === "done" ? "task-completed" : ""}`}
                    key={task.id}
                    data-testid={`task-card-${task.id}`}
                  >
                    <span
                      className={`task-status-icon ${task.status}`}
                      aria-hidden="true"
                    >
                      {task.status === "done"
                        ? "✓"
                        : task.status === "in_progress"
                          ? "◷"
                          : "○"}
                    </span>
                    <div className="task-details">
                      <h3>{task.title}</h3>
                      {task.description && <p>{task.description}</p>}
                      <div className="task-meta">
                        <span className={`status-badge ${task.status}`}>
                          {labels[task.status]}
                        </span>
                        <span className="due-date">
                          {task.due_date ? (
                            <>
                              Due{" "}
                              <time dateTime={task.due_date}>
                                {new Date(
                                  `${task.due_date}T00:00:00`,
                                ).toLocaleDateString("en-GB", {
                                  day: "numeric",
                                  month: "short",
                                  year: "numeric",
                                })}
                              </time>
                            </>
                          ) : (
                            "No due date"
                          )}
                        </span>
                      </div>
                    </div>
                    <div className="task-actions">
                      <button
                        onClick={() => setEditor(task)}
                        aria-label={`Edit ${task.title}`}
                        data-testid={`edit-task-${task.id}`}
                      >
                        Edit
                      </button>
                      <button
                        className="delete-link"
                        onClick={() => setDeleting(task)}
                        aria-label={`Delete ${task.title}`}
                        data-testid={`delete-task-${task.id}`}
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
            <footer className="list-footer">
              <span className="muted">
                {data && data.pagination.total > 0
                  ? `${(page - 1) * limit + 1}–${Math.min(page * limit, data.pagination.total)} of ${data.pagination.total} tasks`
                  : "0 tasks"}
              </span>
              <div className="pagination">
                <label htmlFor="limit" className="sr-only">
                  Tasks per page
                </label>
                <select
                  id="limit"
                  value={limit}
                  onChange={(e) => {
                    setLimit(Number(e.target.value));
                    setPage(1);
                  }}
                  data-testid="page-size"
                >
                  <option value="5">5 / page</option>
                  <option value="10">10 / page</option>
                  <option value="25">25 / page</option>
                  <option value="50">50 / page</option>
                </select>
                <button
                  disabled={busy || !!error || page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  aria-label="Previous page"
                  data-testid="previous-page"
                >
                  ‹
                </button>
                <span data-testid="current-page">
                  {page} / {Math.max(1, data?.pagination.pages || 0)}
                </span>
                <button
                  disabled={
                    busy || !!error || page >= (data?.pagination.pages || 0)
                  }
                  onClick={() => setPage((p) => p + 1)}
                  aria-label="Next page"
                  data-testid="next-page"
                >
                  ›
                </button>
              </div>
            </footer>
          </section>
        </main>
      </div>
      {editor !== undefined && (
        <TaskForm
          task={editor}
          onClose={() => setEditor(undefined)}
          onSaved={() => refreshed(editor ? "Task updated." : "Task created.")}
        />
      )}
      {deleting && (
        <DeleteTask
          task={deleting}
          onClose={() => setDeleting(null)}
          onDeleted={() => refreshed("Task deleted.")}
        />
      )}
    </div>
  );
}
