/** Two-letter initials for an avatar ("Dilmurod Muxsinjonov" -> "DM"). */
export function initials(name: string | null | undefined, fallback = "FB"): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return fallback;
  const letters = parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[parts.length - 1][0];
  return letters.toLocaleUpperCase("uz");
}

/** First name for greetings; falls back to a neutral word. */
export function firstName(name: string | null | undefined, fallback = "do‘stim"): string {
  const first = (name || "").trim().split(/\s+/)[0];
  return first || fallback;
}

const WEEKDAYS = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];

/** "16-noyabr, Yakshanba" without relying on the runtime's uz locale data. */
export function uzDate(d = new Date()): string {
  return `${d.getDate()}-${MONTHS[d.getMonth()]}, ${WEEKDAYS[d.getDay()]}`;
}

/** ISO weekday 1 (Mon) .. 7 (Sun), matching the availability API. */
export function isoWeekday(d = new Date()): number {
  return d.getDay() === 0 ? 7 : d.getDay();
}
