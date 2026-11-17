import { NextRequest } from "next/server";
import { proxyBackendJson } from "@/lib/server/backendProxy";

export async function GET(request: NextRequest) {
  const party = new URL(request.url).searchParams.get("party");
  const qs = party ? `?party=${encodeURIComponent(party)}` : "";
  return proxyBackendJson(request, `/api/v1/me/e-imzo${qs}`, "GET");
}

export async function PUT(request: NextRequest) {
  return proxyBackendJson(request, "/api/v1/me/e-imzo", "PUT");
}
