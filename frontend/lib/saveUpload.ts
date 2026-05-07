import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

export type SaveUploadJobParams = {
  video: File;
  promptText: string;
  outputVideo?: File | null;
};

export type SaveUploadJobResult = {
  jobId: string;
  uploadDir: string;
  videoName: string;
  sourceVideoUrl: string;
  outputVideoName: string | null;
  outputVideoUrl: string | null;
};

export function safeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, "_");
}

export function getRepoRoot(): string {
  return path.basename(process.cwd()) === "frontend"
    ? path.dirname(process.cwd())
    : process.cwd();
}

export function getUploadsRoot(): string {
  return path.join(getRepoRoot(), "frontend", "uploads");
}

export function getUploadDir(jobId: string): string {
  return path.join(getUploadsRoot(), jobId);
}

export function getOutputVideosRoot(): string {
  return path.join(getRepoRoot(), "videos", "output_videos");
}

export function getOutputVideoFilename(jobId: string, rawName: string): string {
  const safeName = safeFilename(rawName || "output-video.mp4");
  return `${jobId}_${safeName}`;
}

export function getOutputVideoUrl(filename: string): string {
  return `/api/output-videos/${filename}`;
}

export async function saveBrowserFile(file: File, outputPath: string): Promise<void> {
  const arrayBuffer = await file.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);
  await writeFile(outputPath, buffer);
}

export async function saveUploadJob({
  video,
  promptText,
  outputVideo,
}: SaveUploadJobParams): Promise<SaveUploadJobResult> {
  const jobId = randomUUID();
  const uploadDir = getUploadDir(jobId);
  await mkdir(uploadDir, { recursive: true });

  const videoName = safeFilename(video.name || "source-video.mp4");
  await saveBrowserFile(video, path.join(uploadDir, videoName));

  let outputVideoName: string | null = null;
  let outputVideoUrl: string | null = null;
  if (outputVideo instanceof File && outputVideo.size > 0) {
    const outputRoot = getOutputVideosRoot();
    await mkdir(outputRoot, { recursive: true });
    outputVideoName = getOutputVideoFilename(jobId, outputVideo.name || "output-video.mp4");
    await saveBrowserFile(outputVideo, path.join(outputRoot, outputVideoName));
    outputVideoUrl = getOutputVideoUrl(outputVideoName);
    await writeFile(
      path.join(uploadDir, "output-video.json"),
      `${JSON.stringify(
        {
          outputVideoName,
          outputVideoUrl,
          updatedAt: new Date().toISOString(),
        },
        null,
        2,
      )}\n`,
      "utf-8",
    );
  }

  await writeFile(path.join(uploadDir, "prompt.txt"), promptText, "utf-8");
  await writeFile(
    path.join(uploadDir, "job.json"),
    `${JSON.stringify(
      {
        jobId,
        videoName,
        prompt: promptText,
      },
      null,
      2,
    )}\n`,
    "utf-8",
  );

  return {
    jobId,
    uploadDir,
    videoName,
    sourceVideoUrl: `/api/video-files/${jobId}/${videoName}`,
    outputVideoName,
    outputVideoUrl,
  };
}
