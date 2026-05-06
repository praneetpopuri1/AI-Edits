"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Save } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";

type PromptTemplates = {
  timeline: string;
  plan: string;
};

type PromptTemplateResponse = {
  templates: PromptTemplates;
  placeholders: Record<keyof PromptTemplates, string[]>;
  updatedAt: string | null;
};

const emptyTemplates: PromptTemplates = {
  timeline: "",
  plan: "",
};

function templateStats(value: string): string {
  const lines = value ? value.split("\n").length : 0;
  return `${lines} lines / ${value.length} chars`;
}

async function fetchPromptTemplates(): Promise<PromptTemplateResponse> {
  const response = await fetch("/api/prompts", { cache: "no-store" });
  const data = (await response.json()) as PromptTemplateResponse | { error?: string };

  if (!response.ok || !("templates" in data)) {
    throw new Error(data.error ?? "Could not load VLM prompts.");
  }

  return data;
}

export function PromptTemplateEditor() {
  const [templates, setTemplates] = useState<PromptTemplates>(emptyTemplates);
  const [lastSavedTemplates, setLastSavedTemplates] = useState<PromptTemplates>(emptyTemplates);
  const [placeholders, setPlaceholders] = useState<PromptTemplateResponse["placeholders"]>({
    timeline: [],
    plan: [],
  });
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const { toast } = useToast();

  const isDirty = useMemo(
    () =>
      templates.timeline !== lastSavedTemplates.timeline ||
      templates.plan !== lastSavedTemplates.plan,
    [templates, lastSavedTemplates],
  );

  const loadTemplates = async () => {
    setIsLoading(true);
    try {
      const data = await fetchPromptTemplates();

      setTemplates(data.templates);
      setLastSavedTemplates(data.templates);
      setPlaceholders(data.placeholders);
      setUpdatedAt(data.updatedAt);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Prompt load failed",
        description: error instanceof Error ? error.message : "Unexpected prompt load error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    fetchPromptTemplates()
      .then((data) => {
        if (!isMounted) return;
        setTemplates(data.templates);
        setLastSavedTemplates(data.templates);
        setPlaceholders(data.placeholders);
        setUpdatedAt(data.updatedAt);
      })
      .catch((error) => {
        if (!isMounted) return;
        toast({
          variant: "destructive",
          title: "Prompt load failed",
          description: error instanceof Error ? error.message : "Unexpected prompt load error",
        });
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [toast]);

  const saveTemplates = async () => {
    setIsSaving(true);
    try {
      const response = await fetch("/api/prompts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ templates }),
      });
      const data = (await response.json()) as PromptTemplateResponse | { error?: string };

      if (!response.ok || !("templates" in data)) {
        throw new Error(data.error ?? "Could not save VLM prompts.");
      }

      setTemplates(data.templates);
      setLastSavedTemplates(data.templates);
      setUpdatedAt(data.updatedAt);
      toast({
        title: "VLM prompts saved",
        description: "Future planner runs will use the updated prompt templates.",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Prompt save failed",
        description: error instanceof Error ? error.message : "Unexpected prompt save error",
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="space-y-5 rounded-xl border border-zinc-700 bg-zinc-950/55 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-[family-name:var(--font-syne)] text-xl text-zinc-100">
              VLM Prompt Templates
            </h2>
            {isDirty ? <Badge variant="outline" className="border-primary/50 text-primary">Unsaved</Badge> : null}
          </div>
          <p className="max-w-3xl text-sm text-zinc-400">
            Review and edit the user-message templates sent to Qwen on pass 1 and pass 2.
            Keep the placeholder tokens where you want runtime metadata, transcript, and contract
            content inserted.
          </p>
          <p className="max-w-3xl text-xs text-zinc-500">
            In pass 2, <span className="font-mono text-zinc-300">[[USER_PROMPT]]</span> is filled
            from the submission form&apos;s prompt field at runtime.
          </p>
          <p className="font-mono text-xs text-zinc-500">
            {updatedAt ? `Last saved ${new Date(updatedAt).toLocaleString()}` : "Using checked-in prompt templates"}
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isLoading || isSaving}
            onClick={loadTemplates}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Reload
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={isLoading || isSaving || !isDirty}
            onClick={saveTemplates}
          >
            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            Save
          </Button>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="timeline-prompt" className="font-mono uppercase tracking-[0.2em] text-zinc-300">
            Pass 1: Timeline Understanding
          </Label>
          <Textarea
            id="timeline-prompt"
            value={templates.timeline}
            disabled={isLoading}
            onChange={(event) => setTemplates((current) => ({ ...current, timeline: event.target.value }))}
            className="min-h-96 border-zinc-700 bg-black/20 font-mono text-xs leading-relaxed"
          />
          <p className="text-xs text-zinc-500">
            Placeholders: {placeholders.timeline.join(", ") || "none"} · {templateStats(templates.timeline)}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="plan-prompt" className="font-mono uppercase tracking-[0.2em] text-zinc-300">
            Pass 2: Edit Plan Generation
          </Label>
          <Textarea
            id="plan-prompt"
            value={templates.plan}
            disabled={isLoading}
            onChange={(event) => setTemplates((current) => ({ ...current, plan: event.target.value }))}
            className="min-h-96 border-zinc-700 bg-black/20 font-mono text-xs leading-relaxed"
          />
          <p className="text-xs text-zinc-500">
            Placeholders: {placeholders.plan.join(", ")} · {templateStats(templates.plan)}
          </p>
        </div>
      </div>
    </section>
  );
}
