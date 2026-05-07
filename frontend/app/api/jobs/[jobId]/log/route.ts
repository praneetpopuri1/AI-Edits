import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { getUploadDir } from "@/lib/saveUpload";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{
    jobId: string;
  }>;
};

function isSafePathSegment(value: string): boolean {
  return /^[a-zA-Z0-9._-]+$/.test(value);
}

export async function GET(_request: Request, context: RouteContext) {
  const { jobId } = await context.params;
  if (!isSafePathSegment(jobId)) {
    return NextResponse.json({ error: "Invalid job ID." }, { status: 400 });
  }

  const logPath = path.join(getUploadDir(jobId), "pipeline.log");

  try {
    const body = await readFile(logPath, "utf-8");
    return new NextResponse(body, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ error: "Log not found." }, { status: 404 });
  }
}
