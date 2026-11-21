export type Status = "todo" | "in_progress" | "done";
export type User = { id: string; email: string };
export type Task = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  status: Status;
  due_date: string | null;
  created_at: string;
  updated_at: string;
};
export type TaskBody = Pick<
  Task,
  "title" | "description" | "status" | "due_date"
>;
export type TaskList = {
  items: Task[];
  pagination: { page: number; limit: number; total: number; pages: number };
};
type Detail = { loc: (string | number)[]; msg: string; type: string };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details: Detail[] = [],
  ) {
    super(message);
  }
}
let csrf: string | null = null;
export function clearCsrf() {
  csrf = null;
}

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  notifyExpired = true,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && !["/auth/login", "/auth/register"].includes(path)) {
    if (!csrf)
      csrf = (await api<{ csrf_token: string }>("/auth/csrf")).csrf_token;
    headers["X-CSRF-Token"] = csrf;
  }
  const response = await fetch(`/api/v1${path}`, {
    method,
    credentials: "same-origin",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    if (
      notifyExpired &&
      response.status === 401 &&
      !["/auth/login", "/auth/register"].includes(path)
    ) {
      clearCsrf();
      window.dispatchEvent(new Event("session-expired"));
    }
    const data = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      data?.error?.message || "The server could not complete your request.",
      data?.error?.details || [],
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function message(error: unknown): string {
  return error instanceof Error
    ? error instanceof TypeError
      ? "Cannot reach the server. Check your connection and try again."
      : error.message
    : "Something went wrong.";
}

export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {};
  return Object.fromEntries(
    error.details
      .filter((d) => d.loc[0] === "body" && d.loc.length > 1)
      .map((d) => [String(d.loc[1]), d.msg.replace(/^Value error, /, "")]),
  );
}
