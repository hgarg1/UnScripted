import { z } from "zod";

export const provenanceTypeSchema = z.enum(["human", "agent", "mixed", "system"]);

export const postSchema = z.object({
  id: z.string(),
  author_account_id: z.string(),
  body: z.string(),
  provenance_type: provenanceTypeSchema,
  moderation_state: z.string(),
  created_at: z.string(),
  like_count: z.number(),
  reply_count: z.number(),
  repost_count: z.number()
});

export const authorSchema = z.object({
  id: z.string(),
  handle: z.string(),
  displayName: z.string()
});

export const feedItemSchema = z.object({
  post: postSchema,
  author: authorSchema,
  rank: z.object({
    score: z.number(),
    reason: z.string()
  })
});

export const feedResponseSchema = z.object({
  items: z.array(feedItemSchema),
  next_cursor: z.string().nullable().optional()
});

export type FeedResponse = z.infer<typeof feedResponseSchema>;

export const authResponseSchema = z.object({
  id: z.string(),
  handle: z.string(),
  display_name: z.string(),
  role: z.string(),
  bio: z.string(),
  is_agent_account: z.boolean(),
  session: z.object({
    token: z.string(),
    expires_at: z.string()
  })
});

export type AuthResponse = z.infer<typeof authResponseSchema>;

export const profileSchema = z.object({
  id: z.string(),
  handle: z.string(),
  display_name: z.string(),
  role: z.string(),
  bio: z.string(),
  declared_interests: z.array(z.string()),
  is_agent_account: z.boolean()
});

export type Profile = z.infer<typeof profileSchema>;

export const discoveryAccountSchema = z.object({
  id: z.string(),
  handle: z.string(),
  display_name: z.string(),
  bio: z.string(),
  is_agent_account: z.boolean(),
  is_following: z.boolean()
});

export const discoveryResponseSchema = z.object({
  items: z.array(discoveryAccountSchema)
});

export type DiscoveryResponse = z.infer<typeof discoveryResponseSchema>;

export const moderationSignalSchema = z.object({
  id: z.string(),
  content_type: z.string(),
  content_id: z.string(),
  signal_type: z.string(),
  score: z.number(),
  source: z.string(),
  status: z.string(),
  created_at: z.string()
});

export type ModerationSignal = z.infer<typeof moderationSignalSchema>;
