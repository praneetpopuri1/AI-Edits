"use client";

import { useState } from "react";
import { Loader2, SendHorizontal } from "lucide-react";

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
  prompt: string;
  savedAt: string;
};

const MAX_PROMPT_LEN = 1000;

export function SubmitSection({ videoFile }: SubmitSectionProps) {
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [serverResponse, setServerResponse] = useState<UploadResponse | null>(null);
  const { toast } = useToast();

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

    const formData = new FormData();
    formData.append("video", videoFile);
    formData.append("prompt", prompt.trim());

    setIsSubmitting(true);
    setUploadProgress(0);
    setServerResponse(null);

    try {
      const response = await new Promise<UploadResponse>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload");
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
      toast({
        title: "Upload complete",
        description: `Job ${response.jobId} created.`,
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
          <p className="font-mono text-xs text-zinc-400">Uploading... {uploadProgress}%</p>
        </div>
      ) : null}

      <Button type="button" className="w-full font-semibold" disabled={isSubmitting} onClick={onSubmit}>
        {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <SendHorizontal className="mr-2 h-4 w-4" />}
        Submit to Backend
      </Button>

      {serverResponse ? (
        <div className="rounded-md border border-zinc-700 bg-black/35 p-3 text-sm text-zinc-200">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-zinc-400">Last response</p>
          <p className="mt-2">Job ID: <span className="font-mono">{serverResponse.jobId}</span></p>
          <p>Video: {serverResponse.videoName}</p>
        </div>
      ) : null}
    </div>
  );
}
