/// <reference types="vite/client" />

import React, { useEffect, useId, useRef, useState } from "react";
import { api, message } from "./api";

type Notice = {
  id: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
};

type NoticePage = { items: Notice[]; total: number; page_size: number };
const configuredInterval = Number(import.meta.env.VITE_NOTIFICATION_POLL_MS);
const pollMs =
  Number.isFinite(configuredInterval) && configuredInterval >= 1000
    ? configuredInterval
    : 5000;

export function Notifications() {
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(0);
  const [data, setData] = useState<NoticePage | null>(null);
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const wrapper = useRef<HTMLDivElement>(null);
  const bell = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const counter = await api<{ count: number }>("/notifications/unread-count");
        if (!active) return;
        setCount(counter.count);
        if (open) {
          const list = await api<NoticePage>(`/notifications?page=${page}`);
          if (!active) return;
          const lastPage = Math.max(1, Math.ceil(list.total / list.page_size));
          if (page > lastPage) {
            setPage(lastPage);
            return;
          }
          setData(list);
        }
        setLoadError("");
      } catch (e) {
        if (active) setLoadError(message(e));
      } finally {
        if (active) timer = setTimeout(refresh, pollMs);
      }
    }
    if (!busy) void refresh();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [open, page, busy]);

  useEffect(() => {
    if (!open) return;
    function outside(event: PointerEvent) {
      if (event.target instanceof Node && !wrapper.current?.contains(event.target)) {
        setOpen(false);
      }
    }
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape" && wrapper.current?.contains(document.activeElement)) {
        setOpen(false);
        bell.current?.focus();
      }
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  async function mutate(path: string, method: string) {
    setBusy(true);
    setActionError("");
    try {
      await api(`/notifications${path}`, method);
    } catch (e) {
      setActionError(message(e));
    } finally {
      setBusy(false);
    }
  }

  function changePage(next: number) {
    setData(null);
    setPage(next);
  }

  return (
    <div className="notifications" ref={wrapper}>
      <button
        type="button"
        ref={bell}
        className="notification-bell"
        aria-label="Notifications"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        data-testid="notification-bell"
        onClick={() => setOpen((value) => !value)}
      >
        <span aria-hidden="true">🔔</span>
        <span className="notification-count" data-testid="notification-unread-count"
          aria-label={`${count} unread`}>
          {count}
        </span>
      </button>
      {open && (
        <section
          className="notification-panel"
          id={panelId}
          aria-label="Notifications"
          data-testid="notification-panel"
        >
          <div className="notification-panel-header">
            <h2>Notifications</h2>
            <button
              type="button"
              disabled={busy || !!loadError || count === 0}
              data-testid="notification-mark-all-read"
              onClick={() => void mutate("/read-all", "POST")}
            >
              Mark all read
            </button>
          </div>
          {(actionError || loadError) && (
            <p role="alert" data-testid="notification-error-state">{actionError || loadError}</p>
          )}
          {!data && !loadError && (
            <p role="status" data-testid="notification-loading-state">Loading notifications…</p>
          )}
          {data && data.items.length === 0 && !loadError && (
            <p data-testid="notification-empty-state">No notifications yet.</p>
          )}
          {!!data?.items.length && (
            <ul className="notification-list" data-testid="notification-list">
              {data.items.map((notice) => (
                <li
                  key={notice.id}
                  className={notice.is_read ? "notification-read" : "notification-unread"}
                  data-testid="notification-item"
                  data-notification-id={notice.id}
                >
                  <h3 data-testid="notification-title">{notice.title}</h3>
                  <p data-testid="notification-message">{notice.message}</p>
                  <time dateTime={notice.created_at} data-testid="notification-created-at">
                    {new Date(notice.created_at).toLocaleString("en-GB")}
                  </time>
                  <div className="notification-actions">
                    <button
                      type="button"
                      disabled={busy || !!loadError}
                      data-testid={notice.is_read ? "notification-mark-unread" : "notification-mark-read"}
                      onClick={() => void mutate(
                        `/${notice.id}/${notice.is_read ? "unread" : "read"}`, "PATCH",
                      )}
                    >
                      {notice.is_read ? "Mark unread" : "Mark read"}
                    </button>
                    <button
                      type="button"
                      disabled={busy || !!loadError}
                      data-testid="notification-delete"
                      onClick={() => void mutate(`/${notice.id}`, "DELETE")}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {data && (page > 1 || data.total > data.page_size) && (
            <nav aria-label="Notification pages" className="notification-actions">
              <button type="button" disabled={busy || page <= 1} onClick={() => changePage(page - 1)}>
                Previous
              </button>
              <span>Page {page}</span>
              <button
                type="button"
                disabled={busy || page * data.page_size >= data.total}
                onClick={() => changePage(page + 1)}
              >
                Next
              </button>
            </nav>
          )}
        </section>
      )}
    </div>
  );
}
