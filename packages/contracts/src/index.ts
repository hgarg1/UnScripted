import { z } from "zod";

export const provenanceTypeSchema = z.enum(["human", "agent", "mixed", "system"]);

export const postSchema = z.object({
  id: z.string(),
  authorAccountId: z.string(),
  body: z.string(),
  provenanceType: provenanceTypeSchema,
  createdAt: z.string()
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
  items: z.array(feedItemSchema)
});

export type FeedResponse = z.infer<typeof feedResponseSchema>;
