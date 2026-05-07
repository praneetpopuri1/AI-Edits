import { spawn } from "node:child_process";
import { closeSync, existsSync, openSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { getRepoRoot, saveUploadJob } from "@/lib/saveUpload";

export const runtime = "nodejs";

function parseBooleanField(value: FormDataEntryValue | null): boolean {
  if (typeof value !== "string") return false;
  return value === "1" || value.toLowerCase() === "true";
}

function nowIso(): string {
  return new Date().toISOString();
}

async function writeWorkerStatus(
  uploadDir: string,
  payload: {
    status: "queued" | "running" | "completed" | "failed";
    step: string;
    message: string;
    error: string | null;
    startedAt: string | null;
    updatedAt: string;
  },
): Promise<void> {
  const statusPath = path.join(uploadDir, "status.json");
  await writeFile(statusPath, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
}

function resolvePythonCommand(): string {
  const fromEnv = process.env.AI_EDITS_PYTHON?.trim();
  if (fromEnv) return fromEnv;
  const venvPython = path.join(getRepoRoot(), ".venv", "bin", "python");
  if (existsSync(venvPython)) {
    return venvPython;
  }
  return "python3";
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
    const startupAt = nowIso();
    await writeWorkerStatus(saved.uploadDir, {
      status: "running",
      step: "worker_startup",
      message: "Pipeline worker is starting.",
      error: null,
      startedAt: startupAt,
      updatedAt: startupAt,
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
    const stdoutPath = path.join(saved.uploadDir, "worker.stdout.log");
    const stderrPath = path.join(saved.uploadDir, "worker.stderr.log");
    const stdoutFd = openSync(stdoutPath, "a");
    const stderrFd = openSync(stderrPath, "a");

    const child = spawn(resolvePythonCommand(), args, {
      cwd: getRepoRoot(),
      detached: true,
      env: { ...process.env, ...dotEnvVars, PYTHONUNBUFFERED: "1" },
      stdio: ["ignore", stdoutFd, stderrFd],
    });
    closeSync(stdoutFd);
    closeSync(stderrFd);

    child.once("error", () => {
      const failedAt = nowIso();
      void writeWorkerStatus(saved.uploadDir, {
        status: "failed",
        step: "worker_startup",
        message: "Failed to start pipeline worker process.",
        error: "Spawn failed. Check worker.stderr.log for details.",
        startedAt: startupAt,
        updatedAt: failedAt,
      });
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
