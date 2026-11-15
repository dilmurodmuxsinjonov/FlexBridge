import { NextRequest } from "next/server";
import { proxyBackendJson } from "@/lib/server/backendProxy";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ code: string }> }
) {
  const { code } = await params;
  return proxyBackendJson(request, `/api/v1/internship-documents/verify/${encodeURIComponent(code)}`, "GET");
}
