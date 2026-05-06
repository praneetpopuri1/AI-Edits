import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";

import { NextResponse } from "next/server";

export const runtime = "nodejs";

function safeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, "_");
}

async function saveFile(file: File, outputPath: string): Promise<void> {
  const arrayBuffer = await file.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);
  await writeFile(outputPath, buffer);
}

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const video = formData.get("video");
    const prompt = formData.get("prompt");

    if (!(video instanceof File)) {
      return NextResponse.json({ error: "Video file is required." }, { status: 400 });
    }

    const promptText = typeof prompt === "string" ? prompt : "";
    const jobId = randomUUID();
    const uploadDir = path.join(process.cwd(), "uploads", jobId);

    await mkdir(uploadDir, { recursive: true });

    const videoName = safeFilename(video.name || "source-video.mp4");
    await saveFile(video, path.join(uploadDir, videoName));

    await writeFile(
      path.join(uploadDir, "prompt.txt"),
      promptText,
      "utf-8",
    );

    return NextResponse.json({
      jobId,
      videoName,
      prompt: promptText,
      savedAt: uploadDir,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown upload error" },
      { status: 500 },
    );
  }
}
