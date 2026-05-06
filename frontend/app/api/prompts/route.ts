import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

export const runtime = "nodejs";

type PromptTemplates = {
  timeline: string;
  plan: string;
};

type PromptTemplateFile = {
  templates?: Partial<PromptTemplates>;
  updatedAt?: string;
};

const PLACEHOLDERS = {
  timeline: ["[[SOURCE_META_JSON]]"],
  plan: [
    "[[USER_PROMPT]]",
    "[[SOURCE_META_JSON]]",
    "[[TIMELINE_EVENTS_JSON]]",
    "[[TRANSCRIPT_WORDS_JSON]]",
    "[[EDIT_PLAN_CONTRACT]]",
  ],
};

function getRepoRoot(): string {
  return path.basename(process.cwd()) === "frontend"
    ? path.dirname(process.cwd())
    : process.cwd();
}

function getPromptTemplatePath(): string {
  return path.join(
    getRepoRoot(),
    "pipeline",
    "planning",
    "shared",
    "prompt_templates.json",
  );
}

function validateTemplates(templates: Partial<PromptTemplates> | undefined): PromptTemplates {
  const timeline = templates?.timeline;
  const plan = templates?.plan;

  if (typeof timeline !== "string" || !timeline.trim()) {
    throw new Error("Pass 1 timeline prompt is required.");
  }

  if (typeof plan !== "string" || !plan.trim()) {
    throw new Error("Pass 2 edit plan prompt is required.");
  }

  return {
    timeline: timeline.trim(),
    plan: plan.trim(),
  };
}

async function readPromptTemplateFile(): Promise<PromptTemplateFile> {
  const raw = await readFile(getPromptTemplatePath(), "utf-8");
  return JSON.parse(raw) as PromptTemplateFile;
}

export async function GET() {
  try {
    const data = await readPromptTemplateFile();
    const templates = validateTemplates(data.templates);

    return NextResponse.json({
      templates,
      placeholders: PLACEHOLDERS,
      updatedAt: data.updatedAt ?? null,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown prompt load error" },
      { status: 500 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as PromptTemplateFile;
    const templates = validateTemplates(body.templates);
    const nextData = {
      templates,
      updatedAt: new Date().toISOString(),
    };

    await writeFile(
      getPromptTemplatePath(),
      `${JSON.stringify(nextData, null, 2)}\n`,
      "utf-8",
    );

    return NextResponse.json({
      ...nextData,
      placeholders: PLACEHOLDERS,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown prompt save error" },
      { status: 400 },
    );
  }
}
