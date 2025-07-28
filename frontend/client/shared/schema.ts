import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, integer, boolean, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  phone: text("phone"),
  country: text("country"),
  isVerified: boolean("is_verified").default(false),
  riskLevel: text("risk_level").default("low"),
  deviceFingerprint: jsonb("device_fingerprint"),
  behaviorProfile: jsonb("behavior_profile"),
  isAdmin: boolean("is_admin").default(false),
  createdAt: timestamp("created_at").defaultNow(),
  lastLogin: timestamp("last_login"),
});

export const transactions = pgTable("transactions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").references(() => users.id).notNull(),
  type: text("type").notNull(), // transfer, deposit, withdrawal
  amount: integer("amount").notNull(), // amount in cents
  recipient: text("recipient"),
  description: text("description"),
  riskScore: integer("risk_score").default(0),
  status: text("status").default("completed"), // completed, pending, blocked
  createdAt: timestamp("created_at").defaultNow(),
});

export const fraudAlerts = pgTable("fraud_alerts", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").references(() => users.id).notNull(),
  transactionId: varchar("transaction_id").references(() => transactions.id),
  alertType: text("alert_type").notNull(),
  severity: text("severity").notNull(), // low, medium, high
  description: text("description").notNull(),
  isResolved: boolean("is_resolved").default(false),
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).omit({
  id: true,
  createdAt: true,
  lastLogin: true,
});

export const insertTransactionSchema = createInsertSchema(transactions).omit({
  id: true,
  createdAt: true,
});

export const insertFraudAlertSchema = createInsertSchema(fraudAlerts).omit({
  id: true,
  createdAt: true,
});

export const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  phone: z.string().min(10, "Please enter a valid phone number"),
  country: z.string().min(2, "Please select a country"),
  agreeToTerms: z.boolean().refine(val => val === true, "You must agree to the terms"),
});

// Backend-compatible schema (without frontend-only fields)
export const registerBackendSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  phone: z.string().min(10, "Please enter a valid phone number"),
});

export const transferSchema = z.object({
  recipient: z.string().email("Please enter a valid email address"),
  amount: z.number().min(0.01, "Amount must be greater than 0"),
  description: z.string().optional(),
});

export const loginSchema = z.object({
  identifier: z.string().min(1, "Please enter your email, username, or phone number"),
  behavioral_challenge: z.object({
    type: z.enum(["typing", "mouse", "touch"]),
    data: z.any(),
  }),
  metrics: z.object({
    device: z.any().optional(),
    geo: z.any().optional(),
    ip: z.string().optional(),
  }).optional(),
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type InsertTransaction = z.infer<typeof insertTransactionSchema>;
export type Transaction = typeof transactions.$inferSelect;
export type InsertFraudAlert = z.infer<typeof insertFraudAlertSchema>;
export type FraudAlert = typeof fraudAlerts.$inferSelect;
export type RegisterInput = z.infer<typeof registerSchema>;
export type TransferInput = z.infer<typeof transferSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
