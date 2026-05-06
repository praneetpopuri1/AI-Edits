import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { getRepoRoot, saveUploadJob } from "@/lib/saveUpload";

export const runtime = "nodejs";

function parseBooleanField(value: FormDataEntryValue | null): boolean {
  if (typeof value !== "string") return false;
  return value === "1" || value.toLowerCase() === "true";
}

async function loadDotEnvDev(): Promise<Record<string, string>> {
  const envPath = path.join(getRepoRoot(), ".env.dev");
  try {
    const raw = await readFile(envPath, "utf-8");
    const entries = raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"))
      .map((line) => {
        const [key, ...rest] = line.split("=");
        return [key, rest.join("=")] as const;
      })
      .filter(([key]) => Boolean(key));

    return Object.fromEntries(entries);
  } catch {
    return {};
  }
}

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const video = formData.get("video");
    const prompt = formData.get("prompt");
    const colabUrl = formData.get("colabUrl");

    if (!(video instanceof File)) {
      return NextResponse.json({ error: "Video file is required." }, { status: 400 });
    }

    if (typeof colabUrl !== "string" || !colabUrl.trim()) {
      return NextResponse.json({ error: "Colab URL is required." }, { status: 400 });
    }

    const promptText = typeof prompt === "string" ? prompt : "";
    const saved = await saveUploadJob({
      video,
      promptText,
      outputVideo: null,
    });

    const args = [
      "-m",
      "pipeline.orchestrate",
      "--job-dir",
      saved.uploadDir,
      "--colab-url",
      colabUrl.trim(),
    ];

    const useFrameArray = parseBooleanField(formData.get("useFrameArray"));
    if (parseBooleanField(formData.get("runWhisper"))) {
      args.push("--run-whisper");
    }
    if (useFrameArray) {
      args.push("--use-frame-array");
    } else {
      const colabVideoPath = formData.get("colabVideoPath");
      if (typeof colabVideoPath === "string" && colabVideoPath.trim()) {
        args.push("--colab-video-path", colabVideoPath.trim());
      } else {
        return NextResponse.json(
          { error: "colabVideoPath is required unless useFrameArray=true." },
          { status: 400 },
        );
      }
    }

    const dotEnvVars = await loadDotEnvDev();
    const child = spawn("python3", args, {
      cwd: getRepoRoot(),
      detached: true,
      env: { ...process.env, ...dotEnvVars },
      stdio: "ignore",
    });
    child.unref();

    return NextResponse.json({
      jobId: saved.jobId,
      videoName: saved.videoName,
      sourceVideoUrl: saved.sourceVideoUrl,
      prompt: promptText,
      status: "queued",
      savedAt: saved.uploadDir,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown pipeline submission error" },
      { status: 500 },
    );
  }
}
