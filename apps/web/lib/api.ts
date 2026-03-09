import type { FeedResponse } from "@unscripted/contracts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getFeed(): Promise<FeedResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/feed`, {
      cache: "no-store",
      headers: {
        "x-unscripted-dev-subject": "dev-user",
        "x-unscripted-dev-handle": "architect"
      }
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as FeedResponse;
  } catch {
    return null;
  }
}
