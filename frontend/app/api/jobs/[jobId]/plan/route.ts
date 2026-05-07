import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { getUploadDir } from "@/lib/saveUpload";

export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{
    jobId: string;
  }>;
};

function isSafePathSegment(value: string): boolean {
  return /^[a-zA-Z0-9._-]+$/.test(value);
}

export async function GET(_request: Request, context: RouteContext) {
  const { jobId } = await context.params;
  if (!isSafePathSegment(jobId)) {
    return NextResponse.json({ error: "Invalid job ID." }, { status: 400 });
  }

  const jobDir = getUploadDir(jobId);
  try {
    const [planResponseRaw, finalPlanRaw, pass1Raw, pass2Raw] = await Promise.all([
      readFile(path.join(jobDir, "plan_response.json"), "utf-8"),
      readFile(path.join(jobDir, "final_edit_plan.json"), "utf-8"),
      readFile(path.join(jobDir, "pass1_raw_response.txt"), "utf-8"),
      readFile(path.join(jobDir, "pass2_raw_response.txt"), "utf-8"),
    ]);

    const planResponse = JSON.parse(planResponseRaw) as {
      timeline_events?: unknown;
      warnings?: unknown;
      pass1_prompt_stats?: Record<string, unknown>;
      pass2_prompt_stats?: Record<string, unknown>;
    };
    const finalEditPlan = JSON.parse(finalPlanRaw);

    return NextResponse.json({
      pass1RawResponse: pass1Raw,
      pass2RawResponse: pass2Raw,
      timelineEvents: planResponse.timeline_events ?? [],
      warnings: planResponse.warnings ?? [],
      finalEditPlan,
      pass1PromptStats: planResponse.pass1_prompt_stats ?? null,
      pass2PromptStats: planResponse.pass2_prompt_stats ?? null,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Plan artifacts are not ready yet." },
      { status: 404 },
    );
  }
}
