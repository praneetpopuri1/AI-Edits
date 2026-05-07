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

  const jobDir = getUploadDir(jobId);
  const statusPath = path.join(jobDir, "status.json");
  const workerStderrPath = path.join(jobDir, "worker.stderr.log");

  try {
    const payload = JSON.parse(await readFile(statusPath, "utf-8"));
    return NextResponse.json(payload);
  } catch {
    try {
      const stderr = (await readFile(workerStderrPath, "utf-8")).trim();
      if (stderr) {
        return NextResponse.json(
          {
            status: "failed",
            step: "worker_startup",
            message: "Pipeline worker crashed during startup.",
            error: stderr.slice(0, 8000),
            startedAt: null,
            updatedAt: new Date().toISOString(),
          },
          { status: 200 },
        );
      }
    } catch {
      // stderr log may not exist yet while worker is still starting.
    }

    return NextResponse.json(
      {
        status: "queued",
        step: "queued",
        message: "Waiting for pipeline worker to start.",
        error: null,
        startedAt: null,
        updatedAt: null,
      },
      { status: 200 },
    );
  }
}
