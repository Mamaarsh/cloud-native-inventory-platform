import { createContext } from "react";

export interface SuccessFeedbackContextValue {
  showSuccess: (message: string) => void;
}

export const SuccessFeedbackContext = createContext<SuccessFeedbackContextValue | undefined>(
  undefined,
);
