"use client";

import { useMemo, useRef, useState } from "react";
import { ImageIcon, UploadCloud, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ImageDropZoneProps = {
  imageFiles: File[];
  onImageChange: (files: File[]) => void;
};

export function ImageDropZone({ imageFiles, onImageChange }: ImageDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const previews = useMemo(
    () =>
      imageFiles.map((file) => ({
        file,
        url: URL.createObjectURL(file),
      })),
    [imageFiles],
  );

  const handleSelection = (fileList: FileList | null) => {
    if (!fileList) return;
    const next = Array.from(fileList).filter((file) => file.type.startsWith("image/"));
    if (!next.length) return;
    onImageChange([...imageFiles, ...next]);
  };

  return (
    <div className="space-y-4">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => handleSelection(e.target.files)}
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
          handleSelection(e.dataTransfer.files);
        }}
        className={cn(
          "rounded-xl border-2 border-dashed p-5 transition-all duration-300",
          isDragging
            ? "border-primary bg-primary/10 shadow-[0_0_30px_rgba(255,69,0,0.22)]"
            : "border-zinc-700 bg-zinc-950/40 hover:border-primary/55",
        )}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-mono text-xs uppercase tracking-[0.2em] text-zinc-400">
            Overlay Images
          </h3>
          <Badge variant="outline" className="font-mono text-zinc-300">
            {imageFiles.length} file(s)
          </Badge>
        </div>

        {imageFiles.length > 0 ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {previews.map(({ file, url }, idx) => (
              <div key={`${file.name}-${idx}`} className="group relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={url}
                  alt={file.name}
                  className="h-28 w-full rounded-md border border-zinc-700 object-cover"
                  onLoad={() => URL.revokeObjectURL(url)}
                />
                <button
                  type="button"
                  className="absolute right-1 top-1 rounded-full bg-black/70 p-1 text-zinc-200 opacity-0 transition group-hover:opacity-100"
                  onClick={() => {
                    const next = imageFiles.filter((_, i) => i !== idx);
                    onImageChange(next);
                  }}
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
                <p className="mt-1 truncate font-mono text-[11px] text-zinc-400">{file.name}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid place-items-center rounded-lg border border-zinc-800 bg-black/20 px-6 py-10 text-center">
            <div className="space-y-2">
              <UploadCloud className="mx-auto h-8 w-8 text-primary" />
              <p className="text-sm text-zinc-300">
                Drop images here to store them with this submission
              </p>
              <p className="font-mono text-xs text-zinc-500">
                PNG, JPG, WebP, GIF
              </p>
            </div>
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" variant="secondary" onClick={() => inputRef.current?.click()}>
            <ImageIcon className="mr-2 h-4 w-4" />
            Add Images
          </Button>
          {imageFiles.length ? (
            <Button type="button" variant="ghost" onClick={() => onImageChange([])}>
              Clear All
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
