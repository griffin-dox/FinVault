// server/index.ts
import express2 from "express";

// server/routes.ts
import { createServer } from "http";

// server/storage.ts
import { randomUUID } from "crypto";
var MemStorage = class {
  users;
  transactions;
  fraudAlerts;
  constructor() {
    this.users = /* @__PURE__ */ new Map();
    this.transactions = /* @__PURE__ */ new Map();
    this.fraudAlerts = /* @__PURE__ */ new Map();
    this.initializeDemoData();
  }
  initializeDemoData() {
    const adminId = randomUUID();
    const adminUser = {
      id: adminId,
      name: "Admin User",
      email: "admin@securebank.com",
      phone: "+1234567890",
      country: "US",
      isVerified: true,
      riskLevel: "low",
      deviceFingerprint: null,
      behaviorProfile: null,
      isAdmin: true,
      createdAt: /* @__PURE__ */ new Date(),
      lastLogin: /* @__PURE__ */ new Date()
    };
    this.users.set(adminId, adminUser);
    const userId = randomUUID();
    const demoUser = {
      id: userId,
      name: "John Doe",
      email: "john.doe@email.com",
      phone: "+1234567891",
      country: "US",
      isVerified: true,
      riskLevel: "low",
      deviceFingerprint: { browser: "Chrome", os: "Windows" },
      behaviorProfile: { typingSpeed: 65, accuracy: 95 },
      isAdmin: false,
      createdAt: /* @__PURE__ */ new Date(),
      lastLogin: /* @__PURE__ */ new Date()
    };
    this.users.set(userId, demoUser);
    const transactions2 = [
      {
        id: randomUUID(),
        userId,
        type: "deposit",
        amount: 35e4,
        recipient: null,
        description: "Salary Deposit",
        riskScore: 15,
        status: "completed",
        createdAt: new Date(Date.now() - 24 * 60 * 60 * 1e3)
      },
      {
        id: randomUUID(),
        userId,
        type: "transfer",
        amount: 8999,
        recipient: "amazon.com",
        description: "Online Purchase",
        riskScore: 25,
        status: "completed",
        createdAt: new Date(Date.now() - 48 * 60 * 60 * 1e3)
      }
    ];
    transactions2.forEach((tx) => this.transactions.set(tx.id, tx));
  }
  // User methods
  async getUser(id) {
    return this.users.get(id);
  }
  async getUserByEmail(email) {
    return Array.from(this.users.values()).find((user) => user.email === email);
  }
  async createUser(insertUser) {
    const id = randomUUID();
    const user = {
      ...insertUser,
      id,
      createdAt: /* @__PURE__ */ new Date(),
      lastLogin: null
    };
    this.users.set(id, user);
    return user;
  }
  async updateUser(id, updates) {
    const user = this.users.get(id);
    if (!user) return void 0;
    const updatedUser = { ...user, ...updates };
    this.users.set(id, updatedUser);
    return updatedUser;
  }
  async getAllUsers() {
    return Array.from(this.users.values());
  }
  // Transaction methods
  async getTransaction(id) {
    return this.transactions.get(id);
  }
  async getTransactionsByUserId(userId) {
    return Array.from(this.transactions.values()).filter((tx) => tx.userId === userId);
  }
  async createTransaction(insertTransaction) {
    const id = randomUUID();
    const transaction = {
      ...insertTransaction,
      id,
      createdAt: /* @__PURE__ */ new Date()
    };
    this.transactions.set(id, transaction);
    return transaction;
  }
  async updateTransaction(id, updates) {
    const transaction = this.transactions.get(id);
    if (!transaction) return void 0;
    const updatedTransaction = { ...transaction, ...updates };
    this.transactions.set(id, updatedTransaction);
    return updatedTransaction;
  }
  async getAllTransactions() {
    return Array.from(this.transactions.values());
  }
  // Fraud Alert methods
  async getFraudAlert(id) {
    return this.fraudAlerts.get(id);
  }
  async getFraudAlertsByUserId(userId) {
    return Array.from(this.fraudAlerts.values()).filter((alert) => alert.userId === userId);
  }
  async createFraudAlert(insertAlert) {
    const id = randomUUID();
    const alert = {
      ...insertAlert,
      id,
      createdAt: /* @__PURE__ */ new Date()
    };
    this.fraudAlerts.set(id, alert);
    return alert;
  }
  async getAllFraudAlerts() {
    return Array.from(this.fraudAlerts.values());
  }
};
var storage = new MemStorage();

// shared/schema.ts
import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, integer, boolean, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";
var users = pgTable("users", {
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
  lastLogin: timestamp("last_login")
});
var transactions = pgTable("transactions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").references(() => users.id).notNull(),
  type: text("type").notNull(),
  // transfer, deposit, withdrawal
  amount: integer("amount").notNull(),
  // amount in cents
  recipient: text("recipient"),
  description: text("description"),
  riskScore: integer("risk_score").default(0),
  status: text("status").default("completed"),
  // completed, pending, blocked
  createdAt: timestamp("created_at").defaultNow()
});
var fraudAlerts = pgTable("fraud_alerts", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").references(() => users.id).notNull(),
  transactionId: varchar("transaction_id").references(() => transactions.id),
  alertType: text("alert_type").notNull(),
  severity: text("severity").notNull(),
  // low, medium, high
  description: text("description").notNull(),
  isResolved: boolean("is_resolved").default(false),
  createdAt: timestamp("created_at").defaultNow()
});
var insertUserSchema = createInsertSchema(users).omit({
  id: true,
  createdAt: true,
  lastLogin: true
});
var insertTransactionSchema = createInsertSchema(transactions).omit({
  id: true,
  createdAt: true
});
var insertFraudAlertSchema = createInsertSchema(fraudAlerts).omit({
  id: true,
  createdAt: true
});
var registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  phone: z.string().min(10, "Please enter a valid phone number"),
  country: z.string().min(2, "Please select a country"),
  agreeToTerms: z.boolean().refine((val) => val === true, "You must agree to the terms")
});
var transferSchema = z.object({
  recipient: z.string().email("Please enter a valid email address"),
  amount: z.number().min(0.01, "Amount must be greater than 0"),
  description: z.string().optional()
});
var loginSchema = z.object({
  email: z.string().email("Please enter a valid email address")
});

// server/routes.ts
import { z as z2 } from "zod";
async function registerRoutes(app2) {
  app2.post("/api/auth/register", async (req, res) => {
    try {
      const userData = registerSchema.parse(req.body);
      const existingUser = await storage.getUserByEmail(userData.email);
      if (existingUser) {
        return res.status(409).json({ message: "User already exists" });
      }
      const user = await storage.createUser({
        name: userData.name,
        email: userData.email,
        phone: userData.phone,
        country: userData.country,
        isVerified: false,
        riskLevel: "low",
        deviceFingerprint: null,
        behaviorProfile: null,
        isAdmin: false
      });
      res.status(201).json({ user: { id: user.id, email: user.email } });
    } catch (error) {
      if (error instanceof z2.ZodError) {
        return res.status(400).json({ message: "Validation error", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.post("/api/auth/login", async (req, res) => {
    try {
      const { email } = loginSchema.parse(req.body);
      const user = await storage.getUserByEmail(email);
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      await storage.updateUser(user.id, { lastLogin: /* @__PURE__ */ new Date() });
      res.json({ user });
    } catch (error) {
      if (error instanceof z2.ZodError) {
        return res.status(400).json({ message: "Validation error", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.post("/api/auth/verify-email", async (req, res) => {
    try {
      const { email } = req.body;
      const user = await storage.getUserByEmail(email);
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      await storage.updateUser(user.id, { isVerified: true });
      res.json({ message: "Email verified successfully" });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.post("/api/auth/complete-onboarding", async (req, res) => {
    try {
      const { userId, deviceFingerprint, behaviorProfile } = req.body;
      const user = await storage.updateUser(userId, {
        deviceFingerprint,
        behaviorProfile
      });
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      res.json({ user });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.get("/api/users", async (req, res) => {
    try {
      const users2 = await storage.getAllUsers();
      res.json({ users: users2 });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.get("/api/users/:id", async (req, res) => {
    try {
      const user = await storage.getUser(req.params.id);
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      res.json({ user });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.get("/api/transactions", async (req, res) => {
    try {
      const { userId } = req.query;
      if (userId) {
        const transactions2 = await storage.getTransactionsByUserId(userId);
        res.json({ transactions: transactions2 });
      } else {
        const transactions2 = await storage.getAllTransactions();
        res.json({ transactions: transactions2 });
      }
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.post("/api/transactions", async (req, res) => {
    try {
      const transactionData = transferSchema.parse(req.body);
      const { userId } = req.body;
      if (!userId) {
        return res.status(400).json({ message: "User ID is required" });
      }
      const riskScore = calculateRiskScore(transactionData.amount, transactionData.recipient);
      const transaction = await storage.createTransaction({
        userId,
        type: "transfer",
        amount: Math.round(transactionData.amount * 100),
        // Convert to cents
        recipient: transactionData.recipient,
        description: transactionData.description || "Transfer",
        riskScore,
        status: riskScore > 80 ? "blocked" : riskScore > 50 ? "pending" : "completed"
      });
      if (riskScore > 70) {
        await storage.createFraudAlert({
          userId,
          transactionId: transaction.id,
          alertType: "high_risk_transaction",
          severity: riskScore > 80 ? "high" : "medium",
          description: `High risk transaction detected: $${transactionData.amount} to ${transactionData.recipient}`,
          isResolved: false
        });
      }
      res.status(201).json({ transaction, riskScore });
    } catch (error) {
      if (error instanceof z2.ZodError) {
        return res.status(400).json({ message: "Validation error", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.get("/api/fraud-alerts", async (req, res) => {
    try {
      const alerts = await storage.getAllFraudAlerts();
      res.json({ alerts });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.put("/api/admin/users/:id", async (req, res) => {
    try {
      const { riskLevel, isAdmin } = req.body;
      const user = await storage.updateUser(req.params.id, {
        riskLevel,
        isAdmin
      });
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      res.json({ user });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });
  app2.put("/api/admin/transactions/:id", async (req, res) => {
    try {
      const { status } = req.body;
      const transaction = await storage.updateTransaction(req.params.id, { status });
      if (!transaction) {
        return res.status(404).json({ message: "Transaction not found" });
      }
      res.json({ transaction });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });
  const httpServer = createServer(app2);
  return httpServer;
}
function calculateRiskScore(amount, recipient) {
  let score = 0;
  if (amount > 5e3) score += 40;
  else if (amount > 1e3) score += 20;
  else if (amount > 100) score += 10;
  if (!recipient.includes(".com") && !recipient.includes(".org")) score += 30;
  if (recipient.includes("unknown")) score += 50;
  score += Math.floor(Math.random() * 25);
  return Math.min(100, score);
}

// server/vite.ts
import express from "express";
import fs from "fs";
import path2 from "path";
import { createServer as createViteServer, createLogger } from "vite";

// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";
var vite_config_default = defineConfig({
  base: "./",
  plugins: [
    react(),
    runtimeErrorOverlay(),
    ...process.env.NODE_ENV !== "production" && process.env.REPL_ID !== void 0 ? [
      await import("@replit/vite-plugin-cartographer").then(
        (m) => m.cartographer()
      )
    ] : []
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "client", "src"),
      "@shared": path.resolve(import.meta.dirname, "shared"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets")
    }
  },
  root: path.resolve(import.meta.dirname, "client"),
  build: {
    outDir: path.resolve(import.meta.dirname, "dist"),
    emptyOutDir: true
  },
  server: {
    fs: {
      strict: true,
      deny: ["**/.*"]
    }
  }
});

// server/vite.ts
import { nanoid } from "nanoid";
var viteLogger = createLogger();
function log(message, source = "express") {
  const formattedTime = (/* @__PURE__ */ new Date()).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true
  });
  console.log(`${formattedTime} [${source}] ${message}`);
}
async function setupVite(app2, server) {
  const serverOptions = {
    middlewareMode: true,
    hmr: { server },
    allowedHosts: true
  };
  const vite = await createViteServer({
    ...vite_config_default,
    configFile: false,
    customLogger: {
      ...viteLogger,
      error: (msg, options) => {
        viteLogger.error(msg, options);
        process.exit(1);
      }
    },
    server: serverOptions,
    appType: "custom"
  });
  app2.use(vite.middlewares);
  app2.use("*", async (req, res, next) => {
    const url = req.originalUrl;
    try {
      const clientTemplate = path2.resolve(
        import.meta.dirname,
        "..",
        "client",
        "index.html"
      );
      let template = await fs.promises.readFile(clientTemplate, "utf-8");
      template = template.replace(
        `src="/src/main.tsx"`,
        `src="/src/main.tsx?v=${nanoid()}"`
      );
      const page = await vite.transformIndexHtml(url, template);
      res.status(200).set({ "Content-Type": "text/html" }).end(page);
    } catch (e) {
      vite.ssrFixStacktrace(e);
      next(e);
    }
  });
}
function serveStatic(app2) {
  const distPath = path2.resolve(import.meta.dirname, "public");
  if (!fs.existsSync(distPath)) {
    throw new Error(
      `Could not find the build directory: ${distPath}, make sure to build the client first`
    );
  }
  app2.use(express.static(distPath));
  app2.use("*", (_req, res) => {
    res.sendFile(path2.resolve(distPath, "index.html"));
  });
}

// server/index.ts
var app = express2();
app.use(express2.json());
app.use(express2.urlencoded({ extended: false }));
app.use((req, res, next) => {
  const start = Date.now();
  const path3 = req.path;
  let capturedJsonResponse = void 0;
  const originalResJson = res.json;
  res.json = function(bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };
  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path3.startsWith("/api")) {
      let logLine = `${req.method} ${path3} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }
      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "\u2026";
      }
      log(logLine);
    }
  });
  next();
});
(async () => {
  const server = await registerRoutes(app);
  app.use((err, _req, res, _next) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";
    res.status(status).json({ message });
    throw err;
  });
  if (app.get("env") === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }
  const port = parseInt(process.env.PORT || "3000", 10);
  server.listen(port, "127.0.0.1", () => {
    log(`serving on port ${port}`);
  });
})();
