// /tablero — for now only "Nueva solicitud" for coordination; the live board arrives in step 4.
import { useState } from "react";
import type { ServiceRequest } from "../api/client";
import { AppShell } from "../components/AppShell";
import { RequestForm } from "../components/RequestForm";
import { RequestResult } from "../components/RequestResult";
import { Card, Notice } from "../components/ui";
import { es } from "../i18n/es";

export function BoardPage() {
  const [created, setCreated] = useState<ServiceRequest[]>([]);
  return (
    <AppShell>
      <h1 className="text-teal">{es.screens["/tablero"]}</h1>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <h2>{es.board.newRequest}</h2>
          <div className="mt-3"><RequestForm coordinator onCreated={(r) => setCreated((c) => [r, ...c])} /></div>
        </Card>
        <div className="space-y-3">
          <Notice>{es.board.liveSoon}</Notice>
          {created.map((r) => <RequestResult key={r.request_id} r={r} />)}
        </div>
      </div>
    </AppShell>
  );
}
