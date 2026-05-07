import type { EditPlan } from "../types/editPlan";

/** Output composition size always matches source dimensions. */
export function getOutputDimensions(plan: EditPlan): { width: number; height: number } {
  return {
    width: plan.source_video.width,
    height: plan.source_video.height,
  };
}
