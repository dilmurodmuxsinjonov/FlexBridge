import { NextResponse } from "next/server";
import { proxyAuthed, readJsonObject, UUID_RE } from "@/lib/server/proxy";

export async function DELETE(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_CONTACT_ID" }, { status: 400 });
  }
  const body = await readJsonObject(request);
  if (!body) {
    return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/me/contacts/${id}`, {
    method: "DELETE",
    body,
    fallbackError: "CONTACT_REMOVE_FAILED",
  });
}
