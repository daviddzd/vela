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
  constructor(public status: number, message: string, public body: any = {}) {
    super(message);
  }
}

export type Option = {
  rank: number; caregiver_id: string; caregiver_name: string; caregiver_type: string;
  travel_min: number; planned_start: string; planned_end: string;
};
export type Approval = {
  request_id: string; patient_id: string; patient_name: string; service_name: string;
  scheduled_for: string; minutes_waiting: number; status_reason: string; options: Option[];
};
export type Visit = {
  assignment_id: string; request_id: string; status: string; scheduled_for: string; planned_start: string;
  travel_min: number; service_name: string; patient_name: string; district_name: string; priority: string;
};
export type FamilyVisit = {
  request_id: string; status: string; status_reason: string | null; scheduled_for: string; service_name: string;
  assignment_id: string | null; caregiver_name: string | null; family_confirmed: boolean | null;
};
export type FamilyOverview = {
  patient_id: string; patient_name: string; can_request_services: boolean; home_care_consent: boolean;
  next_visit: FamilyVisit | null; to_confirm: FamilyVisit[]; recent_requests: FamilyVisit[];
  notices: { message: string; created_at: string }[];
};
export type BoardQueueItem = { request_id: string; priority: string; status_reason: string | null; scheduled_for: string;
  origin: string; service_name: string; patient_name: string; minutes_waiting: number; risk: number };
export type BoardAlert = { alert_id: string; level: string; code: string | null; message: string; created_at: string };
export type Board = {
  now: string; counters: { queued: number; on_the_way: number; in_visit: number; done_today: number };
  queue: BoardQueueItem[]; alerts: BoardAlert[];
  visits: { request_id: string; status: string; priority: string; scheduled_for: string; service_name: string;
    patient_name: string; lat: number; lon: number; caregiver_name: string | null }[];
  staff: { caregiver_id: string; name: string; type: string; lat: number; lon: number }[];
};
export type Service = { service_id: string; name: string; duration_min: number };
export type ServiceRequest = FamilyVisit & { priority: string; caregiver_id: string | null };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    // The API already answers with a Spanish message in `detail`.
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : "", body);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<Me>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  me: () => request<Me>("/api/auth/me"),
  services: () => request<Service[]>("/api/services"),
  board: () => request<Board>("/api/board"),
  simulation: () => request<unknown>("/api/simulation/results"),
  contingency: () => request<unknown>("/api/contingency/current"),
  decideContingency: (eventId: string, mode: string, ids: number[]) =>
    request<unknown>(`/api/contingency/${eventId}/decision`, { method: "POST", body: JSON.stringify({ mode, ids }) }),
  demoState: () => request<unknown>("/api/demo/state"),
  demoScenario: (scenario: string) => request<unknown>("/api/demo/scenario", { method: "POST", body: JSON.stringify({ scenario }) }),
  demoUrgent: (institutionId: string) =>
    request<unknown>("/api/demo/urgent-request", { method: "POST", body: JSON.stringify({ institution_id: institutionId }) }),
  demoCaregiverOut: (caregiverId: string) =>
    request<unknown>("/api/demo/caregiver-out", { method: "POST", body: JSON.stringify({ caregiver_id: caregiverId }) }),
  panorama: <T,>(view: string, params: Record<string, string | undefined> = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
    return request<T>(`/api/panorama/${view}${q.size ? `?${q}` : ""}`);
  },
  createRequest: (body: { patient_id?: string; service_id: string; scheduled_for: string; priority?: string }) =>
    request<ServiceRequest>("/api/requests", { method: "POST", body: JSON.stringify(body) }),
  approvals: () => request<Approval[]>("/api/approvals"),
  approve: (requestId: string, caregiverId: string) =>
    request<ServiceRequest>(`/api/approvals/${requestId}`, { method: "POST", body: JSON.stringify({ caregiver_id: caregiverId }) }),
  myVisits: () => request<Visit[]>("/api/visits/mine"),
  arrive: (id: string) => request<{ status: string }>(`/api/visits/${id}/arrive`, { method: "POST" }),
  finish: (id: string) => request<{ status: string }>(`/api/visits/${id}/finish`, { method: "POST" }),
  familyOverview: () => request<FamilyOverview>("/api/family/overview"),
  confirmVisit: (id: string) => request<{ status: string }>(`/api/family/visits/${id}/confirm`, { method: "POST" }),
};
