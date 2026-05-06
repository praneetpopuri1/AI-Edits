import { NextResponse } from "next/server";
import { saveUploadJob } from "@/lib/saveUpload";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const video = formData.get("video");
    const outputVideo = formData.get("outputVideo") ?? formData.get("renderedVideo");
    const prompt = formData.get("prompt");

    if (!(video instanceof File)) {
      return NextResponse.json({ error: "Video file is required." }, { status: 400 });
    }

    const promptText = typeof prompt === "string" ? prompt : "";
    const saved = await saveUploadJob({
      video,
      promptText,
      outputVideo: outputVideo instanceof File ? outputVideo : null,
    });

    return NextResponse.json({
      jobId: saved.jobId,
      videoName: saved.videoName,
      sourceVideoUrl: saved.sourceVideoUrl,
      outputVideoName: saved.outputVideoName,
      outputVideoUrl: saved.outputVideoUrl,
      prompt: promptText,
      savedAt: saved.uploadDir,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown upload error" },
      { status: 500 },
    );
  }
}
