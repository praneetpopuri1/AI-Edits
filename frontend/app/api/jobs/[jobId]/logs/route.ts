import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { getUploadDir } from "@/lib/saveUpload";

export const runtime = "nodejs";

const MAX_CHARS = 120_000;

type RouteContext = {
  params: Promise<{
    jobId: string;
  }>;
};

function isSafePathSegment(value: string): boolean {
  return /^[a-zA-Z0-9._-]+$/.test(value);
}

function tailText(raw: string): string {
  if (raw.length <= MAX_CHARS) return raw;
  return `…(truncated, showing last ${MAX_CHARS} chars)\n${raw.slice(-MAX_CHARS)}`;
}

async function readTail(filePath: string): Promise<string> {
  try {
    const body = await readFile(filePath, "utf-8");
    return tailText(body);
  } catch {
    return "";
  }
}

export async function GET(_request: Request, context: RouteContext) {
  const { jobId } = await context.params;
  if (!isSafePathSegment(jobId)) {
    return NextResponse.json({ error: "Invalid job ID." }, { status: 400 });
  }

  const jobDir = getUploadDir(jobId);
  const [pipelineLog, workerStderr, workerStdout] = await Promise.all([
    readTail(path.join(jobDir, "pipeline.log")),
    readTail(path.join(jobDir, "worker.stderr.log")),
    readTail(path.join(jobDir, "worker.stdout.log")),
  ]);

  return NextResponse.json({
    pipelineLog,
    workerStderr,
    workerStdout,
    updatedAt: new Date().toISOString(),
  });
}
