import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";
import {
  getOutputVideoFilename,
  getOutputVideoUrl,
  getOutputVideosRoot,
  getUploadDir,
  saveBrowserFile,
} from "@/lib/saveUpload";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{
    jobId: string;
  }>;
};

type OutputVideoMetadata = {
  outputVideoName: string;
  outputVideoUrl: string;
  updatedAt: string;
};

function isSafePathSegment(value: string): boolean {
  return /^[a-zA-Z0-9._-]+$/.test(value);
}

function getJobDir(jobId: string): string {
  return getUploadDir(jobId);
}

function getMetadataPath(jobId: string): string {
  return path.join(getJobDir(jobId), "output-video.json");
}

export async function GET(_request: Request, context: RouteContext) {
  const { jobId } = await context.params;

  if (!isSafePathSegment(jobId)) {
    return NextResponse.json({ error: "Invalid job ID." }, { status: 400 });
  }

  try {
    const metadata = JSON.parse(
      await readFile(getMetadataPath(jobId), "utf-8"),
    ) as OutputVideoMetadata;

    return NextResponse.json(metadata);
  } catch {
    return NextResponse.json({ error: "Output video is not ready yet." }, { status: 404 });
  }
}

export async function POST(request: Request, context: RouteContext) {
  const { jobId } = await context.params;

  if (!isSafePathSegment(jobId)) {
    return NextResponse.json({ error: "Invalid job ID." }, { status: 400 });
  }

  try {
    const formData = await request.formData();
    const outputVideo = formData.get("outputVideo") ?? formData.get("renderedVideo");

    if (!(outputVideo instanceof File) || outputVideo.size === 0) {
      return NextResponse.json({ error: "Output video file is required." }, { status: 400 });
    }

    const jobDir = getJobDir(jobId);
    await mkdir(jobDir, { recursive: true });

    const outputRoot = getOutputVideosRoot();
    await mkdir(outputRoot, { recursive: true });

    const outputVideoName = getOutputVideoFilename(jobId, outputVideo.name || "output-video.mp4");
    await saveBrowserFile(outputVideo, path.join(outputRoot, outputVideoName));

    const metadata: OutputVideoMetadata = {
      outputVideoName,
      outputVideoUrl: getOutputVideoUrl(outputVideoName),
      updatedAt: new Date().toISOString(),
    };

    await writeFile(getMetadataPath(jobId), `${JSON.stringify(metadata, null, 2)}\n`, "utf-8");

    return NextResponse.json(metadata);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown output video upload error" },
      { status: 500 },
    );
  }
}
