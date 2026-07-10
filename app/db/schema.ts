import { sql } from "drizzle-orm";
import { sqliteTable, integer, text } from "drizzle-orm/sqlite-core";

/**
 * SQLite datetime string in the format SQLite's date functions understand
 * (YYYY-MM-DD HH:MM:SS, UTC). Used for `$onUpdate` and manual timestamps.
 */
export function sqliteNow(): string {
  return new Date().toISOString().slice(0, 19).replace("T", " ");
}

const createdAt = () =>
  text("createdAt").default(sql`CURRENT_TIMESTAMP`).notNull();
const updatedAt = () =>
  text("updatedAt")
    .default(sql`CURRENT_TIMESTAMP`)
    .notNull()
    .$onUpdate(() => sqliteNow());

export const users = sqliteTable("users", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  unionId: text("unionId").notNull().unique(),
  name: text("name"),
  email: text("email").unique(),
  passwordHash: text("passwordHash"),
  avatar: text("avatar"),
  role: text("role", { enum: ["user", "admin"] }).default("user").notNull(),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
  lastSignInAt: text("lastSignInAt").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

export const tickets = sqliteTable("tickets", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  description: text("description"),
  category: text("category", {
    enum: ["hardware", "software", "network", "security", "access", "other"],
  }).notNull(),
  status: text("status", {
    enum: ["open", "in_progress", "pending", "resolved", "closed"],
  })
    .default("open")
    .notNull(),
  priority: text("priority", {
    enum: ["low", "medium", "high", "critical"],
  })
    .default("medium")
    .notNull(),
  requesterName: text("requesterName"),
  requesterEmail: text("requesterEmail"),
  assignedTo: integer("assignedTo"),
  createdBy: integer("createdBy"),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
  resolvedAt: text("resolvedAt"),
});

export type Ticket = typeof tickets.$inferSelect;
export type InsertTicket = typeof tickets.$inferInsert;

export const incidents = sqliteTable("incidents", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  description: text("description"),
  status: text("status", {
    enum: ["open", "in_progress", "pending", "resolved"],
  })
    .default("open")
    .notNull(),
  priority: text("priority", {
    enum: ["low", "medium", "high", "critical"],
  })
    .default("medium")
    .notNull(),
  impact: text("impact", {
    enum: ["individual", "team", "department", "company"],
  })
    .default("individual")
    .notNull(),
  assignedTo: integer("assignedTo"),
  createdBy: integer("createdBy"),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
  resolvedAt: text("resolvedAt"),
});

export type Incident = typeof incidents.$inferSelect;
export type InsertIncident = typeof incidents.$inferInsert;

export const chatConversations = sqliteTable("chat_conversations", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  userId: integer("userId"),
  title: text("title"),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
});

export type ChatConversation = typeof chatConversations.$inferSelect;

export const chatMessages = sqliteTable("chat_messages", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  conversationId: integer("conversationId").notNull(),
  role: text("role", { enum: ["user", "assistant"] }).notNull(),
  content: text("content").notNull(),
  createdAt: createdAt(),
});

export type ChatMessage = typeof chatMessages.$inferSelect;

export const activities = sqliteTable("activities", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  userId: integer("userId"),
  type: text("type", {
    enum: [
      "ticket_created",
      "ticket_updated",
      "incident_created",
      "incident_resolved",
      "chat_session",
    ],
  }).notNull(),
  description: text("description"),
  metadata: text("metadata", { mode: "json" }),
  createdAt: createdAt(),
});

export type Activity = typeof activities.$inferSelect;

export const KB_CATEGORIES = [
  "procedimentos",
  "hardware",
  "software",
  "rede",
  "seguranca",
  "acesso",
  "geral",
] as const;

export const knowledgeArticles = sqliteTable("knowledge_articles", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  summary: text("summary"),
  content: text("content").notNull(),
  category: text("category", { enum: KB_CATEGORIES }).default("geral").notNull(),
  tags: text("tags"),
  status: text("status", { enum: ["draft", "published"] })
    .default("published")
    .notNull(),
  views: integer("views").default(0).notNull(),
  authorId: integer("authorId"),
  authorName: text("authorName"),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
});

export type KnowledgeArticle = typeof knowledgeArticles.$inferSelect;
export type InsertKnowledgeArticle = typeof knowledgeArticles.$inferInsert;

export const ASSET_TYPES = [
  "notebook",
  "desktop",
  "servidor",
  "monitor",
  "rede",
  "impressora",
  "mobile",
  "licenca",
  "outro",
] as const;

export const ASSET_STATUSES = [
  "ativo",
  "em_manutencao",
  "em_estoque",
  "aposentado",
] as const;

export const assets = sqliteTable("assets", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  tag: text("tag"),
  type: text("type", { enum: ASSET_TYPES }).default("outro").notNull(),
  status: text("status", { enum: ASSET_STATUSES }).default("ativo").notNull(),
  serialNumber: text("serialNumber"),
  location: text("location"),
  assignedTo: integer("assignedTo"),
  assignedName: text("assignedName"),
  purchaseDate: text("purchaseDate"),
  notes: text("notes"),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
});

export type Asset = typeof assets.$inferSelect;
export type InsertAsset = typeof assets.$inferInsert;
