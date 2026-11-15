import { NextRequest } from "next/server";
import { proxyBackendJson } from "@/lib/server/backendProxy";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return proxyBackendJson(request, `/api/v1/placements/${encodeURIComponent(id)}/conclusion-document/sign`, "POST");
}
