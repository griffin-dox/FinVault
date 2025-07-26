import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { registerSchema, transferSchema, loginSchema } from "@shared/schema";
import { z } from "zod";

export async function registerRoutes(app: Express): Promise<Server> {
  // Auth routes
  app.post("/api/auth/register", async (req, res) => {
    try {
      const userData = registerSchema.parse(req.body);
      
      // Check if user already exists
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
        isAdmin: false,
      });
      
      res.status(201).json({ user: { id: user.id, email: user.email } });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Validation error", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.post("/api/auth/login", async (req, res) => {
    try {
      const { email } = loginSchema.parse(req.body);
      
      const user = await storage.getUserByEmail(email);
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      
      // Update last login
      await storage.updateUser(user.id, { lastLogin: new Date() });
      
      res.json({ user });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Validation error", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.post("/api/auth/verify-email", async (req, res) => {
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

  app.post("/api/auth/complete-onboarding", async (req, res) => {
    try {
      const { userId, deviceFingerprint, behaviorProfile } = req.body;
      
      const user = await storage.updateUser(userId, {
        deviceFingerprint,
        behaviorProfile,
      });
      
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      
      res.json({ user });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // User routes
  app.get("/api/users", async (req, res) => {
    try {
      const users = await storage.getAllUsers();
      res.json({ users });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.get("/api/users/:id", async (req, res) => {
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

  // Transaction routes
  app.get("/api/transactions", async (req, res) => {
    try {
      const { userId } = req.query;
      
      if (userId) {
        const transactions = await storage.getTransactionsByUserId(userId as string);
        res.json({ transactions });
      } else {
        const transactions = await storage.getAllTransactions();
        res.json({ transactions });
      }
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.post("/api/transactions", async (req, res) => {
    try {
      const transactionData = transferSchema.parse(req.body);
      const { userId } = req.body;
      
      if (!userId) {
        return res.status(400).json({ message: "User ID is required" });
      }
      
      // Calculate risk score based on amount and other factors
      const riskScore = calculateRiskScore(transactionData.amount, transactionData.recipient);
      
      const transaction = await storage.createTransaction({
        userId,
        type: "transfer",
        amount: Math.round(transactionData.amount * 100), // Convert to cents
        recipient: transactionData.recipient,
        description: transactionData.description || "Transfer",
        riskScore,
        status: riskScore > 80 ? "blocked" : riskScore > 50 ? "pending" : "completed",
      });
      
      // Create fraud alert if high risk
      if (riskScore > 70) {
        await storage.createFraudAlert({
          userId,
          transactionId: transaction.id,
          alertType: "high_risk_transaction",
          severity: riskScore > 80 ? "high" : "medium",
          description: `High risk transaction detected: $${transactionData.amount} to ${transactionData.recipient}`,
          isResolved: false,
        });
      }
      
      res.status(201).json({ transaction, riskScore });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Validation error", errors: error.errors });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // Fraud alert routes
  app.get("/api/fraud-alerts", async (req, res) => {
    try {
      const alerts = await storage.getAllFraudAlerts();
      res.json({ alerts });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // Admin routes
  app.put("/api/admin/users/:id", async (req, res) => {
    try {
      const { riskLevel, isAdmin } = req.body;
      
      const user = await storage.updateUser(req.params.id, {
        riskLevel,
        isAdmin,
      });
      
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      
      res.json({ user });
    } catch (error) {
      res.status(500).json({ message: "Internal server error" });
    }
  });

  app.put("/api/admin/transactions/:id", async (req, res) => {
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

  const httpServer = createServer(app);
  return httpServer;
}

function calculateRiskScore(amount: number, recipient: string): number {
  let score = 0;
  
  // Amount-based risk
  if (amount > 5000) score += 40;
  else if (amount > 1000) score += 20;
  else if (amount > 100) score += 10;
  
  // Recipient-based risk (simplified)
  if (!recipient.includes('.com') && !recipient.includes('.org')) score += 30;
  if (recipient.includes('unknown')) score += 50;
  
  // Random factor for demo
  score += Math.floor(Math.random() * 25);
  
  return Math.min(100, score);
}
