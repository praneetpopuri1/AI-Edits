import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{
    jobId: string;
    filename: string;
  }>;
};

const VIDEO_CONTENT_TYPES: Record<string, string> = {
  ".mov": "video/quicktime",
  ".mp4": "video/mp4",
  ".m4v": "video/x-m4v",
  ".webm": "video/webm",
};

function isSafePathSegment(value: string): boolean {
  return /^[a-zA-Z0-9._-]+$/.test(value);
}

export async function GET(_request: Request, context: RouteContext) {
  const { jobId, filename } = await context.params;

  if (!isSafePathSegment(jobId) || !isSafePathSegment(filename)) {
    return NextResponse.json({ error: "Invalid video path." }, { status: 400 });
  }

  const uploadsRoot = path.resolve(process.cwd(), "uploads");
  const videoPath = path.resolve(uploadsRoot, jobId, filename);

  if (!videoPath.startsWith(`${uploadsRoot}${path.sep}`)) {
    return NextResponse.json({ error: "Invalid video path." }, { status: 400 });
  }

  try {
    const file = await readFile(videoPath);
    const contentType = VIDEO_CONTENT_TYPES[path.extname(filename).toLowerCase()] ?? "application/octet-stream";

    return new NextResponse(file, {
      headers: {
        "Cache-Control": "no-store",
        "Content-Length": String(file.byteLength),
        "Content-Type": contentType,
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Video not found." },
      { status: 404 },
    );
  }
}
