"""Spanish texts that the BACKEND stores as data (alerts.message is user-facing by schema design).
UI texts live in frontend/src/i18n/es.ts; these are only the ones written into the database."""

ALERT_APPROVAL_PENDING = "Solicitud {request_id} de prioridad alta lleva {minutes} min sin aprobarse."
ALERT_QUEUE_WAIT = "Solicitud {request_id} lleva {minutes} min en cola sin personal disponible."
ALERT_APPROVED_BY_TIMEOUT = ("Solicitud urgente {request_id}: se aplicó la propuesta ({caregiver}) porque pasaron "
                             "{minutes} min sin aprobación. Puedes cambiarla desde Aprobaciones o el tablero.")
