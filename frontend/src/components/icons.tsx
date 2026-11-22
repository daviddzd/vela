// All icons are SVG (lucide-react) and always sit next to a word: never information by icon or color alone.
import {
  AlertTriangle, Ban, Car, CheckCircle2, CircleCheck, CircleDot, ClipboardList, Clock, FlaskConical, Home, Info,
  Lock, type LucideIcon, Mic, Minus, Navigation, Plus, ShieldCheck, Star, ThumbsUp, XCircle, ChevronsDown, ChevronDown,
} from "lucide-react";

export const STATUS_ICON: Record<string, LucideIcon> = {
  registered: ClipboardList, validated: ShieldCheck, queued: Clock, assigned: CircleCheck, in_progress: Home,
  completed: CheckCircle2, closed: Lock, rejected: Ban, cancelled: XCircle, unattended: AlertTriangle,
};
export const COUNTER_ICON: Record<string, LucideIcon> = { queued: Clock, on_the_way: Car, in_visit: Home, done_today: CheckCircle2 };
export const PRIORITY_ICON: Record<string, LucideIcon> = { high: AlertTriangle, medium: Minus, low: ChevronsDown };
export const NOTICE_ICON = { info: Info, ok: CheckCircle2, error: AlertTriangle };
export { AlertTriangle, Ban, CheckCircle2, ChevronDown, CircleDot, FlaskConical, Mic, Navigation, Plus, Star, ThumbsUp };

/** Icon placed before a word. Decorative for screen readers (the word carries the meaning). */
export function Icon({ as: Cmp, className = "" }: { as: LucideIcon; className?: string }) {
  return <Cmp aria-hidden="true" focusable="false" className={`inline-block size-[1.1em] shrink-0 align-[-0.15em] ${className}`} strokeWidth={2.25} />;
}
