import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { motion } from "framer-motion";
import { 
  Users, 
  ArrowLeftRight, 
  AlertTriangle, 
  Clock,
  Search,
  Shield,
  Brain,
  Database,
  Globe,
  Download,
  Settings,
  UserCog,
  TrendingUp,
  CheckCircle
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Add types for API data
interface UserType {
  id: number;
  name: string;
  email: string;
  phone?: string;
  verified_at?: string;
  role: string;
  riskLevel?: string;
  lastLogin?: string;
  isVerified?: boolean;
}
interface TransactionType {
  id: number;
  user_id: number;
  amount: number;
  status: string;
  created_at: string;
}
interface FraudAlertType {
  id: number;
  alertType: string;
  description: string;
  severity: string;
  isResolved?: boolean;
}
interface RiskHeatmapDatum {
  location: string;
  avg_risk: number;
  count: number;
}

function AdminRiskHeatmap({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [data, setData] = useState<RiskHeatmapDatum[]>([]);
  useEffect(() => {
    if (open) {
      apiRequest("GET", "/admin/risk-heatmap").then(res => res.json()).then(setData).catch(() => setData([]));
    }
  }, [open]);
  // Color scale: 0=green, 1=yellow, 2=red
  const getColor = (avg: number) => avg < 0.5 ? "green" : avg < 1.5 ? "yellow" : "red";
  const latlngs = data
    .map((e) => e.location.split(",").map(Number))
    .filter(([lat, lon]) => !isNaN(lat) && !isNaN(lon) && lat && lon);
  let bounds: [[number, number], [number, number]] | undefined = undefined;
  if (latlngs.length >= 1) {
    const lats = latlngs.map(([lat]) => lat);
    const lngs = latlngs.map(([, lon]) => lon);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    bounds = [
      [minLat, minLng],
      [maxLat, maxLng],
    ];
  }
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-3xl relative">
        <button onClick={onClose} className="absolute top-2 right-2 text-gray-500 hover:text-black">✕</button>
        <h2 className="text-xl font-bold mb-2">Risk Heatmap (All Users)</h2>
        <div className="mb-2 flex gap-4">
          <span><span className="inline-block w-4 h-4 rounded-full bg-green-500 mr-1" />Low</span>
          <span><span className="inline-block w-4 h-4 rounded-full bg-yellow-500 mr-1" />Medium</span>
          <span><span className="inline-block w-4 h-4 rounded-full bg-red-500 mr-1" />High</span>
        </div>
        <MapContainer
          style={{ height: 400, width: "100%" }}
          bounds={bounds}
          scrollWheelZoom={true}
          zoom={5}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="&copy; OpenStreetMap contributors"
          />
          {data.map((e, i) => {
            const [lat, lon] = e.location.split(",").map(Number);
            if (isNaN(lat) || isNaN(lon)) return null;
            return (
              <CircleMarker
                key={i}
                center={[lat, lon]}
                radius={10 + Math.log(e.count + 1) * 3}
                color={getColor(e.avg_risk)}
                fillOpacity={0.7}
              >
                <Tooltip>
                  <div>
                    <div>Avg Risk: {e.avg_risk.toFixed(2)}</div>
                    <div>Count: {e.count}</div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}

const SYSTEM_SERVICES = [
  { name: "Fraud Detection AI", icon: Brain },
  { name: "Risk Scoring Engine", icon: Shield },
  { name: "Database", icon: Database },
  { name: "API Gateway", icon: Globe },
  { name: "Login", icon: CheckCircle },
];

export default function Admin() {
  const [searchTerm, setSearchTerm] = useState("");
  const [riskThreshold, setRiskThreshold] = useState([75]);
  const [autoBlockThreshold, setAutoBlockThreshold] = useState([90]);
  const [loginStatus, setLoginStatus] = useState<'red' | 'loading' | 'green'>('red');
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showRiskHeatmap, setShowRiskHeatmap] = useState(false);
  const [serviceStatuses, setServiceStatuses] = useState<('red' | 'loading' | 'green')[]>(['red','red','red','red','red']);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Sequentially animate/check system statuses
  useEffect(() => {
    let cancelled = false;
    async function runChecks() {
      // Fraud Detection AI
      setServiceStatuses(s => [ 'loading', ...s.slice(1) ]);
      await new Promise(res => setTimeout(res, 700));
      setServiceStatuses(s => [ 'green', ...s.slice(1) ]);
      // Risk Scoring Engine
      setServiceStatuses(s => [ s[0], 'loading', ...s.slice(2) ]);
      await new Promise(res => setTimeout(res, 700));
      setServiceStatuses(s => [ s[0], 'green', ...s.slice(2) ]);
      // Database (ping backend)
      setServiceStatuses(s => [ s[0], s[1], 'loading', ...s.slice(3) ]);
      let dbOk = false;
      try {
        const resp = await apiRequest('GET', '/api/ping-db');
        dbOk = resp.ok;
      } catch {}
      setServiceStatuses(s => [ s[0], s[1], dbOk ? 'green' : 'red', ...s.slice(3) ]);
      // API Gateway (ping backend)
      setServiceStatuses(s => [ s[0], s[1], s[2], 'loading', s[4] ]);
      let apiOk = false;
      try {
        const resp = await apiRequest('GET', '/api/ping-api');
        apiOk = resp.ok;
      } catch {}
      setServiceStatuses(s => [ s[0], s[1], s[2], apiOk ? 'green' : 'red', s[4] ]);
      // Login
      setServiceStatuses(s => [ s[0], s[1], s[2], s[3], 'loading' ]);
      await new Promise(res => setTimeout(res, 700));
      setServiceStatuses(s => [ s[0], s[1], s[2], s[3], 'green' ]);
    }
    runChecks();
    return () => { cancelled = true; };
  }, []);

  // Fetch risk rules on mount
  useEffect(() => {
  apiRequest("GET", "/api/admin/risk-rules")
      .then(res => res.json())
      .then(data => {
        const rules = data.rules || [];
        const high = rules.find((r: any) => r.rule === "high_threshold");
        const med = rules.find((r: any) => r.rule === "medium_threshold");
        if (high) setAutoBlockThreshold([Number(high.value)]);
        if (med) setRiskThreshold([Number(med.value)]);
      });
    // Login status animation
    setTimeout(() => setLoginStatus('loading'), 500);
    setTimeout(() => setLoginStatus('green'), 2000);
  }, []);

  // Save settings handler
  const saveSettings = async () => {
    try {
  await apiRequest("PATCH", "/api/admin/adjust-risk", { rule: "high_threshold", value: autoBlockThreshold[0] });
  await apiRequest("PATCH", "/api/admin/adjust-risk", { rule: "medium_threshold", value: riskThreshold[0] });
      toast({ title: "Settings saved successfully" });
    } catch {
      toast({ title: "Failed to save settings", variant: "destructive" });
    }
  };

  const { data: usersData = { users: [] } } = useQuery<{ users: UserType[] }>({
    queryKey: ["/api/admin/users"],
  });
  const { data: transactionsData = { transactions: [] } } = useQuery<{ transactions: TransactionType[] }>({
    queryKey: ["/api/admin/transactions"],
  });
  const { data: fraudAlertsData = { alerts: [] } } = useQuery<{ alerts: FraudAlertType[] }>({
    queryKey: ["/api/admin/fraud-alerts"],
  });
  const users = usersData.users;
  const transactions = transactionsData.transactions;
  const fraudAlerts = fraudAlertsData.alerts;

  const updateUserMutation = useMutation({
    mutationFn: async ({ userId, updates }: { userId: string; updates: any }) => {
      const response = await apiRequest("PUT", `/api/admin/users/${userId}`, updates);
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/admin/users"] });
      toast({ title: "User updated successfully" });
    },
    onError: () => {
      toast({ title: "Failed to update user", variant: "destructive" });
    },
  });

  const updateTransactionMutation = useMutation({
    mutationFn: async ({ transactionId, status }: { transactionId: string; status: string }) => {
      const response = await apiRequest("PUT", `/api/admin/transactions/${transactionId}`, { status });
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/admin/transactions"] });
      toast({ title: "Transaction updated successfully" });
    },
    onError: () => {
      toast({ title: "Failed to update transaction", variant: "destructive" });
    },
  });

  const filteredUsers = users.filter((user: UserType) =>
    user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const stats = {
    totalUsers: users.length,
    totalTransactions: transactions.length,
    fraudAlerts: fraudAlerts.filter((alert: FraudAlertType) => !alert.isResolved).length,
    pendingReviews: transactions.filter((tx: TransactionType) => tx.status === 'pending').length,
  };

  const getRiskLevel = (riskLevel: string) => {
    switch (riskLevel) {
      case "low": return { variant: "default", label: "Low" };
      case "medium": return { variant: "secondary", label: "Medium" };
      case "high": return { variant: "destructive", label: "High" };
      default: return { variant: "default", label: "Low" };
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed": return { variant: "default", label: "Completed" };
      case "pending": return { variant: "secondary", label: "Pending" };
      case "blocked": return { variant: "destructive", label: "Blocked" };
      default: return { variant: "default", label: status };
    }
  };

  // Render landing page if not logged in
  if (!isLoggedIn) {
    return (
      <section className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full flex flex-col items-center">
          <h1 className="text-3xl font-bold mb-4">Admin Portal</h1>
          <p className="mb-6 text-gray-600 text-center">Welcome to the SecureBank Admin Portal. Please login to access the dashboard.</p>
          <Button className="w-full" onClick={() => setIsLoggedIn(true)}>
            Login
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section className="py-8 min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-end mb-4">
          <Button onClick={() => setShowRiskHeatmap(true)} variant="outline">
            View Risk Heatmap
          </Button>
        </div>
        <AdminRiskHeatmap open={showRiskHeatmap} onClose={() => setShowRiskHeatmap(false)} />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
          <p className="text-gray-600">Monitor users, transactions, and fraud detection</p>
        </motion.div>

        {/* Admin Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="grid md:grid-cols-4 gap-6 mb-8"
        >
          <Card className="banking-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Users className="h-5 w-5 text-blue-600" />
                </div>
                <span className="text-sm text-gray-500">Total Users</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stats.totalUsers}</p>
              <p className="text-sm text-green-600">+12% this month</p>
            </CardContent>
          </Card>

          <Card className="banking-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <ArrowLeftRight className="h-5 w-5 text-green-600" />
                </div>
                <span className="text-sm text-gray-500">Transactions</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stats.totalTransactions}</p>
              <p className="text-sm text-green-600">+8% this week</p>
            </CardContent>
          </Card>

          <Card className="banking-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                </div>
                <span className="text-sm text-gray-500">Fraud Alerts</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stats.fraudAlerts}</p>
              <p className="text-sm text-red-600">Requires attention</p>
            </CardContent>
          </Card>

          <Card className="banking-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
                  <Clock className="h-5 w-5 text-yellow-600" />
                </div>
                <span className="text-sm text-gray-500">Pending Reviews</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stats.pendingReviews}</p>
              <p className="text-sm text-yellow-600">Queue management</p>
            </CardContent>
          </Card>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Admin Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* User Management */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Card className="banking-card">
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg font-semibold">User Management</CardTitle>
                    <div className="flex space-x-2">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                        <Input
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          placeholder="Search users..."
                          className="pl-10 w-64"
                        />
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="min-w-full">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-3 text-sm font-medium text-gray-600">User</th>
                          <th className="text-left py-3 text-sm font-medium text-gray-600">Risk Score</th>
                          <th className="text-left py-3 text-sm font-medium text-gray-600">Last Login</th>
                          <th className="text-left py-3 text-sm font-medium text-gray-600">Status</th>
                          <th className="text-left py-3 text-sm font-medium text-gray-600">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {filteredUsers.map((user: UserType) => {
                          const riskInfo = getRiskLevel(user.riskLevel || "low");
                          return (
                            <tr key={user.id}>
                              <td className="py-3">
                                <div className="flex items-center space-x-3">
                                  <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                                    <Users className="h-4 w-4 text-primary" />
                                  </div>
                                  <div>
                                    <p className="text-sm font-medium text-gray-900">{user.name}</p>
                                    <p className="text-xs text-gray-500">{user.email}</p>
                                  </div>
                                </div>
                              </td>
                              <td className="py-3">
                                <Badge variant={riskInfo.variant as any}>
                                  {riskInfo.label}
                                </Badge>
                              </td>
                              <td className="py-3 text-sm text-gray-600">
                                {user.lastLogin ? new Date(user.lastLogin).toLocaleDateString() : 'Never'}
                              </td>
                              <td className="py-3">
                                <Badge variant={user.isVerified ? "default" : "secondary"}>
                                  {user.isVerified ? "Active" : "Pending"}
                                </Badge>
                              </td>
                              <td className="py-3">
                                <div className="flex space-x-2">
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => {
                                      const newRiskLevel = user.riskLevel === "low" ? "medium" : 
                                                          user.riskLevel === "medium" ? "high" : "low";
                                      updateUserMutation.mutate({ 
                                        userId: user.id.toString(), 
                                        updates: { riskLevel: newRiskLevel }
                                      });
                                    }}
                                  >
                                    Edit
                                  </Button>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="text-red-600 hover:text-red-700"
                                  >
                                    Ban
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* System Controls */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <Card className="banking-card">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">System Controls</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Risk Threshold: {riskThreshold[0]}%
                      </label>
                      <Slider
                        value={riskThreshold}
                        onValueChange={setRiskThreshold}
                        max={100}
                        step={1}
                        className="w-full"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Transactions above this threshold require manual review
                      </p>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Auto-Block Threshold: {autoBlockThreshold[0]}%
                      </label>
                      <Slider
                        value={autoBlockThreshold}
                        onValueChange={setAutoBlockThreshold}
                        max={100}
                        step={1}
                        className="w-full"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Transactions above this threshold are automatically blocked
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex space-x-4">
                    <Button 
                      className="banking-button-primary"
                      onClick={saveSettings}
                    >
                      Save Settings
                    </Button>
                    <Button 
                      variant="outline" 
                      className="banking-button-secondary"
                      onClick={() => {
                        setRiskThreshold([75]);
                        setAutoBlockThreshold([90]);
                        toast({ title: "Settings reset to default" });
                      }}
                    >
                      Reset to Default
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Admin Sidebar */}
          <div className="space-y-6">
            {/* Fraud Alerts */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <Card className="banking-card">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold flex items-center">
                    <AlertTriangle className="mr-2 h-5 w-5 text-red-500" />
                    Recent Fraud Alerts
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {fraudAlerts.length > 0 ? (
                      fraudAlerts.slice(0, 3).map((alert: FraudAlertType) => (
                        <div key={alert.id} className="p-3 bg-red-50 rounded-lg border border-red-200">
                          <div className="flex items-start justify-between">
                            <div className="flex items-start space-x-2">
                              <AlertTriangle className="text-red-500 text-sm mt-0.5 h-4 w-4" />
                              <div>
                                <p className="text-sm font-medium text-red-800">{alert.alertType}</p>
                                <p className="text-xs text-red-600">{alert.description}</p>
                                <p className="text-xs text-red-500">Severity: {alert.severity}</p>
                              </div>
                            </div>
                            <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-800">
                              Review
                            </Button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500 text-center py-4">No active fraud alerts</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* System Status */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
            >
              <Card className="banking-card">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">System Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {SYSTEM_SERVICES.map((service, idx) => (
                      <div key={service.name} className="flex justify-between items-center">
                        <div className="flex items-center space-x-2">
                          <service.icon className="h-4 w-4 text-gray-600" />
                          <span className="text-sm text-gray-600">{service.name}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          {serviceStatuses[idx] === 'loading' ? (
                            <span className="w-4 h-4 inline-block border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></span>
                          ) : (
                            <div className={`w-2 h-2 rounded-full ${serviceStatuses[idx] === 'green' ? 'bg-green-400' : 'bg-red-400'}`}></div>
                          )}
                          <span className={`text-sm ${serviceStatuses[idx] === 'green' ? 'text-green-600' : serviceStatuses[idx] === 'loading' ? 'text-blue-600' : 'text-red-600'}`}>
                            {serviceStatuses[idx] === 'loading' ? 'Checking...' : serviceStatuses[idx] === 'green' ? 'Online' : 'Offline'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Quick Actions */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            >
              <Card className="banking-card">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {[
                      { icon: Download, label: "Export Fraud Report" },
                      { icon: Settings, label: "System Settings" },
                      { icon: UserCog, label: "Manage Admins" },
                    ].map((action) => (
                      <Button
                        key={action.label}
                        variant="ghost"
                        className="w-full justify-start p-3 hover:bg-primary/5"
                      >
                        <action.icon className="h-4 w-4 text-primary mr-2" />
                        <span className="text-sm font-medium text-gray-700">{action.label}</span>
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}
