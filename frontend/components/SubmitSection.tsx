"use client";

import { useEffect, useRef, useState } from "react";
import { Copy, Loader2, SendHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";

type SubmitSectionProps = {
  videoFile: File | null;
};

type UploadResponse = {
  jobId: string;
  videoName: string;
  sourceVideoUrl?: string;
  outputVideoName?: string | null;
  outputVideoUrl?: string | null;
  prompt: string;
  savedAt: string;
  status?: string;
};

type OutputVideoResponse = {
  outputVideoName: string;
  outputVideoUrl: string;
  updatedAt: string;
};

type JobStatusResponse = {
  status: "queued" | "running" | "completed" | "failed";
  step: string;
  message: string;
  error: string | null;
  startedAt: string | null;
  updatedAt: string | null;
};

type JobPlanResponse = {
  pass1RawResponse: string;
  pass2RawResponse: string;
  timelineEvents: unknown[];
  warnings: unknown[];
  finalEditPlan: unknown;
  pass1PromptStats: Record<string, unknown> | null;
  pass2PromptStats: Record<string, unknown> | null;
};

type BackendLogsResponse = {
  pipelineLog: string;
  workerStderr: string;
  workerStdout: string;
  updatedAt: string;
};

const MAX_PROMPT_LEN = 1000;
const COLAB_URL_STORAGE_KEY = "ai-edits-colab-url";

export function SubmitSection({ videoFile }: SubmitSectionProps) {
  const [prompt, setPrompt] = useState("");
  const [colabUrl, setColabUrl] = useState(() => {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem(COLAB_URL_STORAGE_KEY) ?? "";
  });
  const [useFrameArray, setUseFrameArray] = useState(false);
  const [colabVideoPath, setColabVideoPath] = useState("");
  const [runWhisper, setRunWhisper] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [backendLogs, setBackendLogs] = useState<BackendLogsResponse | null>(null);
  const [serverResponse, setServerResponse] = useState<UploadResponse | null>(null);
  const [planResponse, setPlanResponse] = useState<JobPlanResponse | null>(null);
  const { toast } = useToast();
  const completionToastSentRef = useRef(false);
  const failureToastSentRef = useRef(false);

  useEffect(() => {
    completionToastSentRef.current = false;
    failureToastSentRef.current = false;
  }, [serverResponse?.jobId]);

  const copyLabel = async (label: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({ title: "Copied", description: label });
    } catch {
      toast({
        variant: "destructive",
        title: "Copy failed",
        description: "Clipboard permission or browser blocked access.",
      });
    }
  };

  useEffect(() => {
    if (!colabUrl) return;
    window.localStorage.setItem(COLAB_URL_STORAGE_KEY, colabUrl);
  }, [colabUrl]);

  useEffect(() => {
    const jobId = serverResponse?.jobId;
    if (!jobId) return;

    let cancelled = false;

    const tick = async () => {
      try {
        const [statusResponse, logsResponse] = await Promise.all([
          fetch(`/api/jobs/${jobId}/status`, { cache: "no-store" }),
          fetch(`/api/jobs/${jobId}/logs`, { cache: "no-store" }),
        ]);

        if (cancelled || !statusResponse.ok) return;

        const nextStatus = (await statusResponse.json()) as JobStatusResponse;
        if (cancelled) return;
        setJobStatus(nextStatus);

        if (logsResponse.ok) {
          const logs = (await logsResponse.json()) as BackendLogsResponse;
          if (!cancelled) setBackendLogs(logs);
        }

        if (nextStatus.status === "completed") {
          const outputResponse = await fetch(`/api/jobs/${jobId}/output`, { cache: "no-store" });
          const planDetailsResponse = await fetch(`/api/jobs/${jobId}/plan`, { cache: "no-store" });
          if (outputResponse.ok) {
            const output = (await outputResponse.json()) as OutputVideoResponse;
            if (cancelled) return;

            let gainedOutput = false;
            setServerResponse((current) => {
              if (!current || current.jobId !== jobId) return current;
              if (current.outputVideoUrl) return current;
              gainedOutput = true;
              return {
                ...current,
                outputVideoName: output.outputVideoName,
                outputVideoUrl: output.outputVideoUrl,
              };
            });
            if (gainedOutput && !completionToastSentRef.current) {
              completionToastSentRef.current = true;
              toast({
                title: "Pipeline complete",
                description: `Job ${jobId} finished rendering.`,
              });
            }
          }

          if (planDetailsResponse.ok) {
            const details = (await planDetailsResponse.json()) as JobPlanResponse;
            if (!cancelled) setPlanResponse(details);
          } else if (!cancelled) {
            setJobStatus((current) => {
              if (!current || current.status !== "completed") return current;
              return {
                ...current,
                message: "Render completed. Waiting for output video metadata...",
              };
            });
          }
        }

        if (nextStatus.status === "failed" && !failureToastSentRef.current) {
          failureToastSentRef.current = true;
          const firstLine =
            nextStatus.error?.split("\n").find((l) => l.trim()) ?? nextStatus.message;
          toast({
            variant: "destructive",
            title: "Pipeline failed",
            description: firstLine.slice(0, 280) + (firstLine.length > 280 ? "…" : ""),
          });
        }
      } catch {
        // Keep polling quietly if transient errors occur.
      }
    };

    void tick();
    const intervalId = window.setInterval(tick, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [serverResponse?.jobId, toast]);

  const onSubmit = async () => {
    if (!videoFile) {
      toast({
        variant: "destructive",
        title: "Video required",
        description: "Please choose a video file before submitting.",
      });
      return;
    }

    if (!prompt.trim()) {
      toast({
        variant: "destructive",
        title: "Prompt required",
        description: "Please add a prompt for the backend model.",
      });
      return;
    }

    if (!colabUrl.trim()) {
      toast({
        variant: "destructive",
        title: "Colab URL required",
        description: "Please add your Colab planner base URL before submitting.",
      });
      return;
    }

    if (!useFrameArray && !colabVideoPath.trim()) {
      toast({
        variant: "destructive",
        title: "Colab video path required",
        description: "Provide a Colab-visible path or enable frame-array mode.",
      });
      return;
    }

    const formData = new FormData();
    formData.append("video", videoFile);
    formData.append("prompt", prompt.trim());
    formData.append("colabUrl", colabUrl.trim());
    formData.append("useFrameArray", useFrameArray ? "true" : "false");
    formData.append("runWhisper", runWhisper ? "true" : "false");
    if (!useFrameArray) {
      formData.append("colabVideoPath", colabVideoPath.trim());
    }

    setIsSubmitting(true);
    setUploadProgress(0);
    setJobStatus(null);
    setBackendLogs(null);
    setServerResponse(null);
    setPlanResponse(null);

    try {
      const response = await new Promise<UploadResponse>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/pipeline/run");
        xhr.responseType = "json";

        xhr.upload.onprogress = (event) => {
          if (!event.lengthComputable) return;
          const nextProgress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(nextProgress);
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(xhr.response as UploadResponse);
            return;
          }
          reject(new Error((xhr.response?.error as string) ?? "Upload failed"));
        };

        xhr.onerror = () => reject(new Error("Network error while uploading"));
        xhr.send(formData);
      });

      setServerResponse(response);
      setUploadProgress(100);
      setJobStatus({
        status: "queued",
        step: "queued",
        message: "Pipeline job queued.",
        error: null,
        startedAt: null,
        updatedAt: null,
      });
      toast({
        title: "Pipeline started",
        description: `Job ${response.jobId} was submitted.`,
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Unexpected upload error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 rounded-xl border border-zinc-700 bg-zinc-950/55 p-5">
      <div className="space-y-2">
        <Label htmlFor="colab-url" className="font-mono uppercase tracking-[0.2em] text-zinc-300">
          Colab Planner URL
        </Label>
        <input
          id="colab-url"
          value={colabUrl}
          onChange={(event) => setColabUrl(event.target.value)}
          placeholder="https://your-colab-service-url"
          className="h-10 w-full rounded-md border border-zinc-700 bg-black/20 px-3 text-sm"
        />
        <Label htmlFor="colab-video-path" className="font-mono uppercase tracking-[0.2em] text-zinc-300">
          Colab Video Path
        </Label>
        <input
          id="colab-video-path"
          value={colabVideoPath}
          disabled={useFrameArray}
          onChange={(event) => setColabVideoPath(event.target.value)}
          placeholder="/content/drive/MyDrive/path/to/video.mp4"
          className="h-10 w-full rounded-md border border-zinc-700 bg-black/20 px-3 text-sm disabled:opacity-50"
        />
        <div className="flex flex-wrap items-center gap-6 pt-1 text-sm text-zinc-300">
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={useFrameArray}
              onChange={(event) => setUseFrameArray(event.target.checked)}
            />
            Use frame-array mode
          </label>
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={runWhisper}
              onChange={(event) => setRunWhisper(event.target.checked)}
            />
            Run Whisper locally
          </label>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="prompt" className="font-mono uppercase tracking-[0.2em] text-zinc-300">
          Prompt for VLM
        </Label>
        <Textarea
          id="prompt"
          value={prompt}
          maxLength={MAX_PROMPT_LEN}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Tell the model what edits you want (remove filler, tighten pacing, add emphasis on key points...)"
          className="min-h-32 border-zinc-700 bg-black/20 font-medium"
        />
        <p className="text-right font-mono text-xs text-zinc-500">
          {prompt.length}/{MAX_PROMPT_LEN}
        </p>
      </div>

      {isSubmitting ? (
        <div className="space-y-2">
          <Progress value={uploadProgress} />
          <p className="font-mono text-xs text-zinc-400">Uploading payload... {uploadProgress}%</p>
        </div>
      ) : null}

      {jobStatus ? (
        <div
          className={`space-y-2 rounded-md border p-3 ${
            jobStatus.status === "failed"
              ? "border-destructive/60 bg-destructive/5"
              : "border-zinc-800 bg-zinc-950/60"
          }`}
        >
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-zinc-400">Pipeline status</p>
          <p className="text-sm text-zinc-200">
            Step: <span className="font-mono">{jobStatus.step}</span>
            {jobStatus.status === "failed" ? (
              <span className="ml-2 font-mono text-xs text-destructive">failed</span>
            ) : null}
          </p>
          <p className="text-xs text-zinc-400">{jobStatus.message}</p>
          {jobStatus.error ? (
            <div className="space-y-2">
              <p className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-zinc-500">
                status.json error (python traceback)
              </p>
              <pre className="max-h-96 overflow-auto rounded border border-zinc-800 bg-black/50 p-2 font-mono text-[0.7rem] leading-snug text-zinc-300">
                {jobStatus.error}
              </pre>
              {serverResponse?.jobId ? (
                <a
                  href={`/api/jobs/${serverResponse.jobId}/log`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex font-mono text-xs text-primary underline-offset-4 hover:underline"
                >
                  Open raw pipeline.log
                </a>
              ) : null}
            </div>
          ) : null}
          {backendLogs &&
          (backendLogs.pipelineLog || backendLogs.workerStderr || backendLogs.workerStdout) ? (
            <details
              className="rounded border border-zinc-800 bg-black/40"
              open={jobStatus.status !== "completed"}
            >
              <summary className="cursor-pointer p-2 font-mono text-[0.65rem] uppercase tracking-[0.15em] text-zinc-400">
                Backend logs (pipeline + worker stdout/stderr)
              </summary>
              <div className="space-y-3 border-t border-zinc-800 p-2">
                {backendLogs.pipelineLog ? (
                  <div className="space-y-1">
                    <p className="font-mono text-[0.6rem] text-zinc-500">pipeline.log</p>
                    <pre className="max-h-48 overflow-auto rounded border border-zinc-800/80 bg-black/60 p-2 font-mono text-[0.65rem] text-zinc-300">
                      {backendLogs.pipelineLog}
                    </pre>
                  </div>
                ) : null}
                {backendLogs.workerStderr ? (
                  <div className="space-y-1">
                    <p className="font-mono text-[0.6rem] text-amber-500/90">worker.stderr.log (Remotion, overlay resolver, etc.)</p>
                    <pre className="max-h-48 overflow-auto rounded border border-amber-900/40 bg-black/60 p-2 font-mono text-[0.65rem] text-zinc-300">
                      {backendLogs.workerStderr}
                    </pre>
                  </div>
                ) : null}
                {backendLogs.workerStdout ? (
                  <div className="space-y-1">
                    <p className="font-mono text-[0.6rem] text-zinc-500">worker.stdout.log</p>
                    <pre className="max-h-36 overflow-auto rounded border border-zinc-800/80 bg-black/60 p-2 font-mono text-[0.65rem] text-zinc-300">
                      {backendLogs.workerStdout}
                    </pre>
                  </div>
                ) : null}
              </div>
            </details>
          ) : null}
          <Progress
            value={
              jobStatus.status === "failed"
                ? 0
                : jobStatus.status === "completed"
                  ? 100
                  : jobStatus.step === "rendering"
                    ? 90
                    : jobStatus.step === "planning"
                      ? 60
                      : jobStatus.step === "preprocessing"
                        ? 30
                        : 10
            }
          />
        </div>
      ) : null}

      <Button type="button" className="w-full font-semibold" disabled={isSubmitting} onClick={onSubmit}>
        {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <SendHorizontal className="mr-2 h-4 w-4" />}
        Submit to Backend
      </Button>

      {serverResponse ? (
        <div className="space-y-4 rounded-md border border-zinc-700 bg-black/35 p-3 text-sm text-zinc-200">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-zinc-400">Last response</p>
          <p className="mt-2">Job ID: <span className="font-mono">{serverResponse.jobId}</span></p>
          <p>Video: {serverResponse.videoName}</p>

          {serverResponse.outputVideoUrl ? (
            <div className="space-y-2">
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-zinc-400">Output video</p>
              <div className="flex justify-center rounded-lg border border-zinc-700 bg-black p-2">
                <video
                  controls
                  preload="metadata"
                  src={serverResponse.outputVideoUrl}
                  className="max-h-[70vh] w-auto max-w-full rounded-md bg-black"
                >
                  <track kind="captions" />
                </video>
              </div>
              <a
                href={serverResponse.outputVideoUrl}
                download={serverResponse.outputVideoName ?? "output-video.mp4"}
                className="inline-flex font-mono text-xs text-primary underline-offset-4 hover:underline"
              >
                Download output video
              </a>
            </div>
          ) : (
            <p
              className={`rounded-md border p-3 text-xs ${
                jobStatus?.status === "failed"
                  ? "border-destructive/40 bg-destructive/5 text-zinc-300"
                  : "border-zinc-800 bg-zinc-950/60 text-zinc-500"
              }`}
            >
              {jobStatus?.status === "failed"
                ? "Pipeline failed — see error details above. Fix the issue and submit again."
                : "Rendering is in progress. The output video will appear automatically when complete."}
            </p>
          )}

          {planResponse ? (
            <div className="space-y-3 rounded-md border border-zinc-800 bg-zinc-950/60 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-zinc-400">
                  Plan details (pass 1 / pass 2 / final JSON)
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 font-mono text-xs"
                  onClick={() =>
                    void copyLabel(
                      "Pass 1 + 2 + final JSON",
                      JSON.stringify(
                        {
                          pass1RawResponse: planResponse.pass1RawResponse,
                          pass2RawResponse: planResponse.pass2RawResponse,
                          finalEditPlan: planResponse.finalEditPlan,
                          warnings: planResponse.warnings,
                          pass1PromptStats: planResponse.pass1PromptStats,
                          pass2PromptStats: planResponse.pass2PromptStats,
                        },
                        null,
                        2,
                      ),
                    )
                  }
                >
                  <Copy className="mr-1.5 h-3.5 w-3.5" />
                  Copy all
                </Button>
              </div>

              {Array.isArray(planResponse.warnings) && planResponse.warnings.length > 0 ? (
                <div className="rounded border border-amber-900/50 bg-amber-950/20 p-2">
                  <p className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-amber-200/90">
                    Colab planner warnings
                  </p>
                  <ul className="mt-1 list-inside list-disc font-mono text-[0.7rem] text-zinc-300">
                    {planResponse.warnings.map((w, i) => (
                      <li key={i}>{String(w)}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {planResponse.pass2PromptStats && Object.keys(planResponse.pass2PromptStats).length > 0 ? (
                <div className="space-y-1 rounded border border-zinc-800 bg-zinc-900/40 p-2">
                  <p className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-zinc-400">
                    Pass 2 prompt size (from Colab processor)
                  </p>
                  <pre className="max-h-40 overflow-auto font-mono text-[0.7rem] leading-snug text-zinc-300">
                    {JSON.stringify(planResponse.pass2PromptStats, null, 2)}
                  </pre>
                </div>
              ) : null}

              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-zinc-500">
                    Pass 1 raw response
                  </p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 font-mono text-xs text-zinc-400"
                    onClick={() => void copyLabel("Pass 1 raw response", planResponse.pass1RawResponse || "")}
                  >
                    <Copy className="mr-1 h-3 w-3" />
                    Copy
                  </Button>
                </div>
                <pre className="max-h-56 overflow-auto rounded border border-zinc-800 bg-black/50 p-2 font-mono text-[0.7rem] leading-snug text-zinc-300">
                  {planResponse.pass1RawResponse || "(empty)"}
                </pre>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-zinc-500">
                    Pass 2 raw response
                  </p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 font-mono text-xs text-zinc-400"
                    onClick={() => void copyLabel("Pass 2 raw response", planResponse.pass2RawResponse || "")}
                  >
                    <Copy className="mr-1 h-3 w-3" />
                    Copy
                  </Button>
                </div>
                <pre className="max-h-56 overflow-auto rounded border border-zinc-800 bg-black/50 p-2 font-mono text-[0.7rem] leading-snug text-zinc-300">
                  {planResponse.pass2RawResponse || "(empty)"}
                </pre>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-zinc-500">
                    Final edit plan JSON (saved in edit_plans/)
                  </p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 font-mono text-xs text-zinc-400"
                    onClick={() =>
                      void copyLabel(
                        "Final edit plan JSON",
                        JSON.stringify(planResponse.finalEditPlan, null, 2),
                      )
                    }
                  >
                    <Copy className="mr-1 h-3 w-3" />
                    Copy
                  </Button>
                </div>
                <pre className="max-h-72 overflow-auto rounded border border-zinc-800 bg-black/50 p-2 font-mono text-[0.7rem] leading-snug text-zinc-300">
                  {JSON.stringify(planResponse.finalEditPlan, null, 2)}
                </pre>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
