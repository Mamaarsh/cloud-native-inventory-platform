import { apiClient } from "@/api/client";
import type { TokenPair, TokenRequest, User } from "@/types";

export async function requestTokens(credentials: TokenRequest): Promise<TokenPair> {
  const { data } = await apiClient.post<TokenPair>("/auth/token/", credentials);
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<User>("/auth/me/");
  return data;
}
