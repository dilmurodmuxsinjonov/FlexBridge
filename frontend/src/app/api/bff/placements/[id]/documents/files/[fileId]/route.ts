import { NextRequest } from "next/server";
import { proxyBackendFileStream } from "@/lib/server/backendProxy";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; fileId: string }> }
) {
  const { id, fileId } = await params;
  return proxyBackendFileStream(
    `/api/v1/placements/${encodeURIComponent(id)}/documents/files/${encodeURIComponent(fileId)}/download`
  );
}
