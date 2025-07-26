import { type User, type InsertUser, type Transaction, type InsertTransaction, type FraudAlert, type InsertFraudAlert } from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  // Users
  getUser(id: string): Promise<User | undefined>;
  getUserByEmail(email: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  updateUser(id: string, updates: Partial<User>): Promise<User | undefined>;
  getAllUsers(): Promise<User[]>;
  
  // Transactions
  getTransaction(id: string): Promise<Transaction | undefined>;
  getTransactionsByUserId(userId: string): Promise<Transaction[]>;
  createTransaction(transaction: InsertTransaction): Promise<Transaction>;
  updateTransaction(id: string, updates: Partial<Transaction>): Promise<Transaction | undefined>;
  getAllTransactions(): Promise<Transaction[]>;
  
  // Fraud Alerts
  getFraudAlert(id: string): Promise<FraudAlert | undefined>;
  getFraudAlertsByUserId(userId: string): Promise<FraudAlert[]>;
  createFraudAlert(alert: InsertFraudAlert): Promise<FraudAlert>;
  getAllFraudAlerts(): Promise<FraudAlert[]>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private transactions: Map<string, Transaction>;
  private fraudAlerts: Map<string, FraudAlert>;

  constructor() {
    this.users = new Map();
    this.transactions = new Map();
    this.fraudAlerts = new Map();
    
    // Initialize with some demo data
    this.initializeDemoData();
  }

  private initializeDemoData() {
    // Create admin user
    const adminId = randomUUID();
    const adminUser: User = {
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
      createdAt: new Date(),
      lastLogin: new Date(),
    };
    this.users.set(adminId, adminUser);

    // Create demo regular user
    const userId = randomUUID();
    const demoUser: User = {
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
      createdAt: new Date(),
      lastLogin: new Date(),
    };
    this.users.set(userId, demoUser);

    // Create demo transactions
    const transactions = [
      {
        id: randomUUID(),
        userId,
        type: "deposit",
        amount: 350000,
        recipient: null,
        description: "Salary Deposit",
        riskScore: 15,
        status: "completed",
        createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000),
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
        createdAt: new Date(Date.now() - 48 * 60 * 60 * 1000),
      },
    ];

    transactions.forEach(tx => this.transactions.set(tx.id, tx as Transaction));
  }

  // User methods
  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByEmail(email: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(user => user.email === email);
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = randomUUID();
    const user: User = {
      ...insertUser,
      id,
      createdAt: new Date(),
      lastLogin: null,
    };
    this.users.set(id, user);
    return user;
  }

  async updateUser(id: string, updates: Partial<User>): Promise<User | undefined> {
    const user = this.users.get(id);
    if (!user) return undefined;
    
    const updatedUser = { ...user, ...updates };
    this.users.set(id, updatedUser);
    return updatedUser;
  }

  async getAllUsers(): Promise<User[]> {
    return Array.from(this.users.values());
  }

  // Transaction methods
  async getTransaction(id: string): Promise<Transaction | undefined> {
    return this.transactions.get(id);
  }

  async getTransactionsByUserId(userId: string): Promise<Transaction[]> {
    return Array.from(this.transactions.values()).filter(tx => tx.userId === userId);
  }

  async createTransaction(insertTransaction: InsertTransaction): Promise<Transaction> {
    const id = randomUUID();
    const transaction: Transaction = {
      ...insertTransaction,
      id,
      createdAt: new Date(),
    };
    this.transactions.set(id, transaction);
    return transaction;
  }

  async updateTransaction(id: string, updates: Partial<Transaction>): Promise<Transaction | undefined> {
    const transaction = this.transactions.get(id);
    if (!transaction) return undefined;
    
    const updatedTransaction = { ...transaction, ...updates };
    this.transactions.set(id, updatedTransaction);
    return updatedTransaction;
  }

  async getAllTransactions(): Promise<Transaction[]> {
    return Array.from(this.transactions.values());
  }

  // Fraud Alert methods
  async getFraudAlert(id: string): Promise<FraudAlert | undefined> {
    return this.fraudAlerts.get(id);
  }

  async getFraudAlertsByUserId(userId: string): Promise<FraudAlert[]> {
    return Array.from(this.fraudAlerts.values()).filter(alert => alert.userId === userId);
  }

  async createFraudAlert(insertAlert: InsertFraudAlert): Promise<FraudAlert> {
    const id = randomUUID();
    const alert: FraudAlert = {
      ...insertAlert,
      id,
      createdAt: new Date(),
    };
    this.fraudAlerts.set(id, alert);
    return alert;
  }

  async getAllFraudAlerts(): Promise<FraudAlert[]> {
    return Array.from(this.fraudAlerts.values());
  }
}

export const storage = new MemStorage();
