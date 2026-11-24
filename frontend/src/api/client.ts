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
  relay_caregiver_id: string | null; relay_caregiver_name: string | null; relay_at: string | null;
};
export type Approval = {
  request_id: string; patient_id: string; patient_name: string; service_name: string;
  scheduled_for: string; minutes_waiting: number; status_reason: string; options: Option[];
};
export type Visit = {
  assignment_id: string; request_id: string; status: string; scheduled_for: string; planned_start: string;
  travel_min: number; service_name: string; patient_name: string; district_name: string; priority: string; patient_id: string;
  relay_role: "first" | "relay" | null; relay_partner_name: string | null; relay_at: string | null;
  step: "arrive" | "finish" | "wait" | "done";
  arrived_at: string | null; arrive_from: string | null; expected_min: number | null;
};
export type FamilyVisit = {
  request_id: string; status: string; status_reason: string | null; scheduled_for: string; service_name: string;
  assignment_id: string | null; caregiver_name: string | null; family_confirmed: boolean | null;
  relay_caregiver_name?: string | null; relay_at?: string | null;
};
export type FamilyOverview = {
  patient_id: string; patient_name: string; can_request_services: boolean; home_care_consent: boolean;
  next_visit: FamilyVisit | null; to_confirm: FamilyVisit[]; recent_requests: FamilyVisit[];
  notices: { message: string; created_at: string }[];
};
export type BoardQueueItem = { request_id: string; patient_id: string; priority: string; status_reason: string | null; scheduled_for: string;
  origin: string; service_name: string; patient_name: string; minutes_waiting: number; risk: number };
export type BoardAlert = { alert_id: string; type: string; level: string; code: string | null; message: string; created_at: string;
  escalate_at: string | null; escalated_at: string | null };
export type Board = {
  now: string; counters: { queued: number; on_the_way: number; in_visit: number; done_today: number };
  queue: BoardQueueItem[]; alerts: BoardAlert[];
  visits: { request_id: string; patient_id: string; status: string; priority: string; scheduled_for: string; service_name: string;
    patient_name: string; lat: number; lon: number; caregiver_name: string | null;
    relay_caregiver_name: string | null; relay_at: string | null }[];
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
  demoVoice: (institutionId: string, kind: string) =>
    request<any>("/api/demo/voice-sample", { method: "POST", body: JSON.stringify({ institution_id: institutionId, kind }) }),
  voicePatients: () => request<any[]>("/api/voice/patients"),
  voiceText: (patientId: string, text: string) =>
    request<any>("/api/voice/text", { method: "POST", body: JSON.stringify({ patient_id: patientId, text }) }),
  voiceCallMe: (patientId: string) =>
    request<any>("/api/voice/call-me", { method: "POST", body: JSON.stringify({ patient_id: patientId }) }),
  voiceReports: () => request<any[]>("/api/voice/reports"),
  patients: () => request<any[]>("/api/patients"),
  patientRecord: (id: string) => request<any>(`/api/patients/${encodeURIComponent(id)}/record`),
  addPlan: (id: string, body: Record<string, unknown>) =>
    request<any>(`/api/patients/${encodeURIComponent(id)}/care-plans`, { method: "POST", body: JSON.stringify(body) }),
  changePlan: (id: string, plan: string, body: Record<string, unknown>) =>
    request<any>(`/api/patients/${encodeURIComponent(id)}/care-plans/${plan}`, { method: "PUT", body: JSON.stringify(body) }),
  endPlan: (id: string, plan: string) =>
    request<any>(`/api/patients/${encodeURIComponent(id)}/care-plans/${plan}/end`, { method: "POST" }),
  staff: () => request<any>("/api/staff"),
  staffCoverage: () => request<any>("/api/staff/coverage"),
  staffDay: (id: string, on?: string) => request<any>(`/api/staff/${id}/day${on ? `?on=${on}` : ""}`),
  staffOut: (id: string, reason: string) =>
    request<any>(`/api/staff/${id}/out-of-service`, { method: "POST", body: JSON.stringify({ reason }) }),
  staffRestDay: (id: string, restDay: number) =>
    request<any>(`/api/staff/${id}/rest-day`, { method: "PUT", body: JSON.stringify({ rest_day: restDay }) }),
  staffBack: (id: string) => request<any>(`/api/staff/${id}/back-in-service`, { method: "POST" }),
  business: () => request<any>("/api/business"),
  businessModel: (values: Record<string, unknown>) =>
    request<any>("/api/business/model", { method: "POST", body: JSON.stringify({ values }) }),
  privacyNotice: () => request<{ markdown: string; arco_days: number }>("/api/privacy/notice"),
  consents: (q = "") => request<any>(`/api/privacy/consents${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  recordConsent: (body: Record<string, unknown>) =>
    request<any>("/api/privacy/consents", { method: "POST", body: JSON.stringify(body) }),
  revokeConsent: (id: string, reason: string) =>
    request<any>(`/api/privacy/consents/${id}/revoke`, { method: "POST", body: JSON.stringify({ reason }) }),
  arcoCreate: (body: Record<string, string>) => request<any>("/api/privacy/arco", { method: "POST", body: JSON.stringify(body) }),
  arcoList: () => request<any[]>("/api/privacy/arco"),
  audit: (params: Record<string, string>) =>
    request<any>(`/api/privacy/audit?${new URLSearchParams(Object.entries(params).filter(([, v]) => v))}`),
  auditSummary: () => request<any>("/api/privacy/audit/summary"),
  voiceReview: (id: string) => request<any>(`/api/voice/reports/${id}/review`, { method: "POST" }),
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
  finish: (id: string, confirm = false) =>
    request<{ status: string }>(`/api/visits/${id}/finish${confirm ? "?confirm=true" : ""}`, { method: "POST" }),
  reviewAlert: (id: string, outcome: "emergency" | "not_emergency") =>
    request<unknown>(`/api/alerts/${id}/review`, { method: "POST", body: JSON.stringify({ outcome }) }),
  escalatedAlerts: () => request<any[]>("/api/alerts/escalated"),
  acknowledgeAlert: (id: string) => request<unknown>(`/api/alerts/${id}/acknowledge`, { method: "POST" }),
  familyOverview: () => request<FamilyOverview>("/api/family/overview"),
  confirmVisit: (id: string) => request<{ status: string }>(`/api/family/visits/${id}/confirm`, { method: "POST" }),
};
