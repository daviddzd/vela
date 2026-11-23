// "relevo: Ana López a las 03:00" — a 12-h service covered by two consecutive people (dispatcher.relay_options).
import { es } from "../i18n/es";
import { formatTime } from "./format";

export function relayText(name: string | null | undefined, at: string | null | undefined): string {
  return name && at ? es.relay.with.replace("{name}", name).replace("{time}", formatTime(at)) : "";
}
