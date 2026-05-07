import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";

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

function buildRangeResponse(
  rangeHeader: string,
  fileSize: number,
): { start: number; end: number } | null {
  const match = /^bytes=(\d*)-(\d*)$/.exec(rangeHeader.trim());
  if (!match) return null;

  const [, startRaw, endRaw] = match;
  const start = startRaw === "" ? 0 : Number.parseInt(startRaw, 10);
  const end = endRaw === "" ? fileSize - 1 : Number.parseInt(endRaw, 10);

  if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
  if (start < 0 || end < start || start >= fileSize) return null;

  return { start, end: Math.min(end, fileSize - 1) };
}

export async function GET(request: Request, context: RouteContext) {
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
    const fileStat = await stat(videoPath);
    const fileSize = fileStat.size;
    const contentType = VIDEO_CONTENT_TYPES[path.extname(filename).toLowerCase()] ?? "application/octet-stream";
    const rangeHeader = request.headers.get("range");

    if (rangeHeader) {
      const parsedRange = buildRangeResponse(rangeHeader, fileSize);
      if (!parsedRange) {
        return new NextResponse(null, {
          status: 416,
          headers: {
            "Accept-Ranges": "bytes",
            "Content-Range": `bytes */${fileSize}`,
            "Cache-Control": "no-store",
          },
        });
      }

      const { start, end } = parsedRange;
      const stream = createReadStream(videoPath, { start, end });

      return new NextResponse(Readable.toWeb(stream) as ReadableStream, {
        status: 206,
        headers: {
          "Accept-Ranges": "bytes",
          "Cache-Control": "no-store",
          "Content-Length": String(end - start + 1),
          "Content-Range": `bytes ${start}-${end}/${fileSize}`,
          "Content-Type": contentType,
        },
      });
    }

    const stream = createReadStream(videoPath);
    return new NextResponse(Readable.toWeb(stream) as ReadableStream, {
      headers: {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Content-Length": String(fileSize),
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
