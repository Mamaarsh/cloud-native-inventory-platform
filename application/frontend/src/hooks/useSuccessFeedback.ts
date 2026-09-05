import { useContext } from "react";
import { SuccessFeedbackContext } from "@/feedback/SuccessFeedbackContext";

export function useSuccessFeedback() {
  const context = useContext(SuccessFeedbackContext);
  if (!context) throw new Error("useSuccessFeedback must be used within SuccessFeedbackProvider.");
  return context;
}
