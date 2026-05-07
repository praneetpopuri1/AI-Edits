"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Film, UploadCloud, Video } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type VideoDropZoneProps = {
  videoFile: File | null;
  onVideoChange: (file: File | null) => void;
};

function formatBytes(size: number): string {
  if (size === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(size) / Math.log(k));
  return `${(size / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export function VideoDropZone({ videoFile, onVideoChange }: VideoDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [duration, setDuration] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const previewUrl = useMemo(() => (videoFile ? URL.createObjectURL(videoFile) : null), [videoFile]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const handleVideoSelect = (fileList: FileList | null) => {
    const file = fileList?.[0];
    if (!file) return;
    if (!file.type.startsWith("video/")) return;
    setDuration(null);
    onVideoChange(file);
  };

  return (
    <div className="space-y-4">
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={(e) => handleVideoSelect(e.target.files)}
      />
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleVideoSelect(e.dataTransfer.files);
        }}
        className={cn(
          "group relative overflow-hidden rounded-xl border-2 border-dashed p-6 transition-all duration-300",
          isDragging
            ? "border-primary bg-primary/10 shadow-[0_0_30px_rgba(255,69,0,0.3)]"
            : "border-zinc-700 bg-zinc-950/60 hover:border-primary/60",
        )}
      >
        <div className="absolute inset-0 opacity-20 [background:repeating-linear-gradient(90deg,transparent,transparent_14px,rgba(255,255,255,0.07)_14px,rgba(255,255,255,0.07)_16px)]" />
        <div className="relative z-10 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-mono text-xs uppercase tracking-[0.2em] text-zinc-400">Source Video</h3>
            <Film className="h-4 w-4 text-primary" />
          </div>

          {previewUrl ? (
            <div className="space-y-3">
              <div className="flex justify-center rounded-lg border border-zinc-700 bg-black p-2">
                <video
                  src={previewUrl}
                  controls
                  preload="metadata"
                  className="max-h-[70vh] w-auto max-w-full rounded-md bg-black"
                  onLoadedMetadata={(e) => {
                    setDuration(e.currentTarget.duration);
                  }}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary" className="font-mono">
                  <Video className="mr-1 h-3 w-3" />
                  {videoFile?.name ?? "selected-video"}
                </Badge>
                {videoFile ? (
                  <Badge variant="outline" className="font-mono text-zinc-300">
                    {formatBytes(videoFile.size)}
                  </Badge>
                ) : null}
                {videoFile && duration ? (
                  <Badge variant="outline" className="font-mono text-zinc-300">
                    {duration.toFixed(1)}s
                  </Badge>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="grid place-items-center rounded-lg border border-zinc-800 bg-black/20 px-6 py-12 text-center">
              <div className="space-y-3">
                <UploadCloud className="mx-auto h-10 w-10 text-primary" />
                <p className="text-sm text-zinc-300">
                  Drop your video here or browse from disk
                </p>
                <p className="font-mono text-xs text-zinc-500">
                  MP4, MOV, MKV, WebM
                </p>
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <Button type="button" onClick={() => inputRef.current?.click()}>
              Choose Video
            </Button>
            {videoFile ? (
              <Button type="button" variant="secondary" onClick={() => onVideoChange(null)}>
                Remove
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
