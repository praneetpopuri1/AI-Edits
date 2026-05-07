import React from "react";
import { AbsoluteFill } from "remotion";
import type { EditPlan } from "../types/editPlan";

type Props = {
  plan: EditPlan;
  children: React.ReactNode;
};

export const ReframeWrapper: React.FC<Props> = ({ children }) => {
  return <AbsoluteFill>{children}</AbsoluteFill>;
};
