import { proxyAuthed } from "@/lib/server/proxy";

/**
 * Chat BFF: forwards only the chat API's own routes (allowlist below) to
 * /api/v1/chat/*. Mutations go through proxyAuthed's CSRF origin check.
 */
const U = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const ROUTES: Array<{ methods: string[]; re: RegExp }> = [
  { methods: ["GET"], re: /^me$/ },
  { methods: ["POST"], re: /^me\/contact-code\/rotate$/ },
  { methods: ["GET"], re: /^contacts$/ },
  { methods: ["GET"], re: /^conversations$/ },
  { methods: ["GET"], re: new RegExp(`^conversations/${U}$`, "i") },
  { methods: ["GET", "POST"], re: new RegExp(`^conversations/${U}/messages$`, "i") },
  { methods: ["POST"], re: new RegExp(`^conversations/${U}/read$`, "i") },
  { methods: ["POST"], re: /^direct$/ },
  { methods: ["POST"], re: /^groups$/ },
  { methods: ["PATCH"], re: new RegExp(`^groups/${U}$`, "i") },
  { methods: ["POST"], re: new RegExp(`^groups/${U}/members$`, "i") },
  { methods: ["DELETE"], re: new RegExp(`^groups/${U}/members/${U}$`, "i") },
  { methods: ["POST", "DELETE"], re: new RegExp(`^groups/${U}/invite-link$`, "i") },
  { methods: ["POST"], re: /^join$/ },
  { methods: ["DELETE"], re: new RegExp(`^messages/${U}$`, "i") },
  { methods: ["POST", "DELETE"], re: new RegExp(`^blocks/${U}$`, "i") },
];
const QUERY_KEYS = ["q", "before", "limit"];

type Ctx = { params: Promise<{ path: string[] }> };

async function handle(request: Request, ctx: Ctx, method: "GET" | "POST" | "PATCH" | "DELETE") {
  const { path } = await ctx.params;
  const joined = (path || []).join("/");
  if (!ROUTES.some((r) => r.methods.includes(method) && r.re.test(joined))) {
    return Response.json({ ok: false, error: "NOT_FOUND" }, { status: 404 });
  }
  const incoming = new URL(request.url).searchParams;
  const qs = new URLSearchParams();
  if (method === "GET") {
    for (const k of QUERY_KEYS) {
      const v = incoming.get(k);
      if (v && v.length <= 80) qs.set(k, v);
    }
  }
  let body: unknown = undefined;
  if (method === "POST" || method === "PATCH") {
    const text = await request.text();
    if (text.length > 20_000) return Response.json({ ok: false, error: "INVALID_INPUT" }, { status: 413 });
    try {
      body = text ? JSON.parse(text) : {};
    } catch {
      return Response.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
    }
  }
  const suffix = qs.toString() ? `?${qs}` : "";
  return proxyAuthed(request, `/api/v1/chat/${joined}${suffix}`, { method, body, fallbackError: "CHAT_REQUEST_FAILED" });
}

export const GET = (r: Request, c: Ctx) => handle(r, c, "GET");
export const POST = (r: Request, c: Ctx) => handle(r, c, "POST");
export const PATCH = (r: Request, c: Ctx) => handle(r, c, "PATCH");
export const DELETE = (r: Request, c: Ctx) => handle(r, c, "DELETE");
