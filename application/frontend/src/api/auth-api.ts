import { apiClient } from "@/api/client";
import type {
  PasswordChangeRequest,
  PasswordChangeResponse,
  TokenPair,
  TokenRequest,
  User,
  UserProfileUpdateRequest,
} from "@/types";

export async function requestTokens(credentials: TokenRequest): Promise<TokenPair> {
  const { data } = await apiClient.post<TokenPair>("/auth/token/", credentials);
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<User>("/auth/me/");
  return data;
}

export async function updateCurrentUserProfile(payload: UserProfileUpdateRequest): Promise<User> {
  const { data } = await apiClient.patch<User>("/auth/me/", payload);
  return data;
}

export async function changeCurrentUserPassword(
  payload: PasswordChangeRequest,
): Promise<PasswordChangeResponse> {
  const { data } = await apiClient.post<PasswordChangeResponse>(
    "/auth/change-password/",
    payload,
  );
  return data;
}
