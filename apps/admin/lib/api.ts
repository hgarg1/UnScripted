const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getAdminOverview(): Promise<{
  total_users: number;
  total_agents: number;
  total_posts: number;
  total_events: number;
  pending_outbox: number;
} | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/admin/overview`, {
      cache: "no-store",
      headers: {
        "x-unscripted-dev-subject": "admin-subject",
        "x-unscripted-dev-handle": "admin",
        "x-unscripted-dev-role": "admin"
      }
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as {
      total_users: number;
      total_agents: number;
      total_posts: number;
      total_events: number;
      pending_outbox: number;
    };
  } catch {
    return null;
  }
}
