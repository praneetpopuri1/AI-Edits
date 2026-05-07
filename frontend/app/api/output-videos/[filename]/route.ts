import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { getOutputVideosRoot } from "@/lib/saveUpload";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{
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
  const { filename } = await context.params;

  if (!isSafePathSegment(filename)) {
    return NextResponse.json({ error: "Invalid output video path." }, { status: 400 });
  }

  const outputRoot = path.resolve(getOutputVideosRoot());
  const videoPath = path.resolve(outputRoot, filename);

  if (!videoPath.startsWith(`${outputRoot}${path.sep}`)) {
    return NextResponse.json({ error: "Invalid output video path." }, { status: 400 });
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
      { error: error instanceof Error ? error.message : "Output video not found." },
      { status: 404 },
    );
  }
}
