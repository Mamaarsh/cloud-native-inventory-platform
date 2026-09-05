import axios from "axios";

function firstMessage(value: unknown): string | undefined {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    for (const entry of value) {
      const message = firstMessage(entry);
      if (message) return message;
    }
  }
  if (value && typeof value === "object") {
    for (const [field, entry] of Object.entries(value)) {
      const message = firstMessage(entry);
      if (message) return field === "detail" || field === "non_field_errors" ? message : `${field}: ${message}`;
    }
  }
  return undefined;
}

export function getApiErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : "Something went wrong. Please try again.";
  }

  const backendMessage = firstMessage(error.response?.data);
  if (backendMessage) return backendMessage;

  switch (error.response?.status) {
    case 400:
      return "The request could not be processed. Review the entered values.";
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You do not have permission to perform this action.";
    case 404:
      return "The requested record was not found.";
    default:
      return error.response && error.response.status >= 500
        ? "The server encountered an error. Please try again shortly."
        : "Unable to reach the service. Check your connection and try again.";
  }
}
