"use client";

import { useState } from "react";
import { Clapperboard, Sparkles } from "lucide-react";

import { PromptTemplateEditor } from "@/components/PromptTemplateEditor";
import { SubmitSection } from "@/components/SubmitSection";
import { VideoDropZone } from "@/components/VideoDropZone";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function HomePage() {
  const [videoFile, setVideoFile] = useState<File | null>(null);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8 space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-3 py-1 font-mono text-xs uppercase tracking-[0.24em] text-primary">
          <Sparkles className="h-3.5 w-3.5" />
          The Cutting Room
        </div>
        <h1 className="font-[family-name:var(--font-syne)] text-4xl tracking-tight text-zinc-100 sm:text-5xl">
          Upload. Prompt. Render.
        </h1>
        <p className="max-w-3xl text-zinc-300">
          Submit your source media and creative direction in one place. This UI sends video and
          prompt text to the backend upload API.
        </p>
      </div>

      <Card className="border-zinc-700/80 bg-zinc-900/45 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 font-[family-name:var(--font-syne)] text-2xl">
            <Clapperboard className="h-5 w-5 text-primary" />
            Project Intake
          </CardTitle>
          <CardDescription>
            Provide the media and prompt needed by the VLM pipeline.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <VideoDropZone videoFile={videoFile} onVideoChange={setVideoFile} />
          <Separator className="bg-zinc-800" />
          <SubmitSection videoFile={videoFile} />
          <Separator className="bg-zinc-800" />
          <PromptTemplateEditor />
        </CardContent>
      </Card>
    </main>
  );
}
