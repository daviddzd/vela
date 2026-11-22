// Small fetch wrapper. The session lives in an httpOnly cookie, so JavaScript never sees the token;
// `credentials: "include"` makes the browser send it.

export type Me = {
  user_id: string;
  display_name: string;
  role: string;
  institution_id: string | null;
  home: string;       // first screen for this role
  screens: string[];  // screens this role may open (decided by the API)
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    // The API already answers with a Spanish message in `detail`.
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : "");
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<Me>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  me: () => request<Me>("/api/auth/me"),
};
