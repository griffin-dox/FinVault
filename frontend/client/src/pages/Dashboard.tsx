import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { 
  CreditCard, 
  PiggyBank, 
  ArrowUpRight, 
  ArrowDownLeft, 
  ExternalLink,
  Shield,
  CheckCircle,
  TrendingUp,
  Plus,
  History,
  Settings,
  Headphones
} from "lucide-react";
import { Link } from "wouter";
import TransferModal from "@/components/TransferModal";
import { useEffect, useState } from "react";
import { formatAmountByCountry } from "@/lib/api";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { apiRequest } from "@/lib/queryClient";
import { Table, TableHead, TableRow, TableHeader, TableBody, TableCell } from "@/components/ui/table";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const EVENT_COLORS = {
  login_success: "green",
  login_failure: "red",
  transaction_allowed: "blue",
  transaction_blocked: "orange",
};

// Add types for events and devices
interface HeatmapTile {
  tile_lat: number;
  tile_lon: number;
  count: number;
  avgAcc?: number;
}

interface Device {
  credential_id: string;
  device?: string;
  aaguid?: string;
  created_at?: string;
}

interface Transaction {
  id: string;
  type: 'deposit' | 'withdrawal';
  description: string;
  createdAt: string;
  amount: number;
  riskScore: number;
}

function Heatmap() {
  const { user } = useAuth();
  const [tiles, setTiles] = useState<HeatmapTile[]>([]);
  const [days, setDays] = useState(90);
  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!user?.id) return;
      try {
        const res = await apiRequest("GET", `/api/geo/users/${user.id}/heatmap?days=${days}`);
        const json = await res.json();
        if (!cancelled) setTiles(Array.isArray(json.tiles) ? json.tiles : []);
      } catch {
        if (!cancelled) setTiles([]);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [user?.id, days]);
  // Compute bounds
  const latlngs = tiles.map(t => [t.tile_lat, t.tile_lon] as [number, number]).filter(([a,b]) => !isNaN(a) && !isNaN(b));
  const bounds: [[number, number], [number, number]] = latlngs.length > 0
    ? latlngs.reduce<[[number, number], [number, number]]>(
        (acc, cur) => [
          [Math.min(acc[0][0], cur[0]), Math.min(acc[0][1], cur[1])],
          [Math.max(acc[1][0], cur[0]), Math.max(acc[1][1], cur[1])],
        ],
        [latlngs[0], latlngs[0]]
      )
    : [
        [20.5937, 78.9629],
        [20.5937, 78.9629],
      ]; // Default fallback
  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <span className="text-sm text-gray-600">Window:</span>
        <Button size="sm" variant={days===30?"default":"outline"} onClick={() => setDays(30)}>30d</Button>
        <Button size="sm" variant={days===90?"default":"outline"} onClick={() => setDays(90)}>90d</Button>
        <Button size="sm" variant={days===180?"default":"outline"} onClick={() => setDays(180)}>180d</Button>
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
        {tiles.map((t, i) => (
          <CircleMarker
            key={i}
            center={[t.tile_lat, t.tile_lon]}
            radius={6 + Math.log(t.count + 1) * 2}
            color={t.avgAcc && t.avgAcc > 500 ? "orange" : "#2563eb"}
            fillOpacity={0.6}
          >
            <Tooltip>
              <div>
                <div>Events: {t.count}</div>
                {typeof t.avgAcc === 'number' && <div>Avg accuracy: {t.avgAcc.toFixed(0)}m</div>}
              </div>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}

// Device Management UI
function DeviceManagement() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removeId, setRemoveId] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const [showDialog, setShowDialog] = useState(false);

  useEffect(() => {
    async function fetchDevices() {
      setLoading(true);
      setError(null);
      try {
  const res = await apiRequest("GET", "/api/auth/webauthn/devices");
        if (!res.ok) {
          // Try to parse error as JSON, fallback to text
          let errorMsg = "Failed to fetch devices";
          try {
            const errJson = await res.json();
            errorMsg = errJson.detail || JSON.stringify(errJson);
          } catch {
            const errText = await res.text();
            errorMsg = errText.startsWith('<') ? 'Authentication required or server error.' : errText;
          }
          throw new Error(errorMsg);
        }
        const data = await res.json();
        setDevices(data.devices || []);
      } catch (e: any) {
        setError(e.message || "Failed to fetch devices");
      }
      setLoading(false);
    }
    fetchDevices();
  }, []);

  async function handleRemove(id: string) {
    setRemoveId(id);
    setRemoving(true);
    try {
  const res = await apiRequest("POST", "/api/auth/webauthn/device/remove", { credential_id: id });
      if (!res.ok) throw new Error("Failed to remove device");
      setDevices(devices.filter(d => d.credential_id !== id));
      setShowDialog(false);
    } catch (e) {
      // Optionally show error
    }
    setRemoving(false);
    setRemoveId(null);
  }

  return (
    <div className="mt-8">
      <h2 className="text-xl font-semibold mb-2">Device Management</h2>
      <div className="bg-white rounded shadow p-4">
        {loading ? (
          <div className="text-center py-8">Loading devices...</div>
        ) : error ? (
          <div className="text-red-600">{error}</div>
        ) : devices.length === 0 ? (
          <div className="text-gray-500">No registered devices found.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Device</TableHead>
                <TableHead>Registered At</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {devices.map(device => (
                <TableRow key={device.credential_id}>
                  <TableCell>{device.device || device.aaguid || "Unknown"}</TableCell>
                  <TableCell>{device.created_at ? new Date(device.created_at).toLocaleString() : "-"}</TableCell>
                  <TableCell>
                    <Button variant="destructive" size="sm" onClick={() => { setRemoveId(device.credential_id); setShowDialog(true); }}>
                      Remove
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent>
          <DialogTitle>Remove Device</DialogTitle>
          <DialogDescription>
            Are you sure you want to remove this device? You will not be able to use it for biometric login until you re-register it.
          </DialogDescription>
          <div className="flex gap-2 justify-end mt-4">
            <Button variant="secondary" onClick={() => setShowDialog(false)} disabled={removing}>Cancel</Button>
            <Button variant="destructive" onClick={() => handleRemove(removeId!)} disabled={removing}>
              {removing ? "Removing..." : "Remove"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(false);

  const { data: transactionsData = { transactions: [] } } = useQuery<{ transactions: Transaction[] }>({
    queryKey: ["/api/transaction", String(user?.id ?? "")],
    enabled: !!user?.id,
  });
  const transactions = transactionsData.transactions || [];

  const recentTransactions = transactions.slice(0, 3);

  const getRiskColor = (riskScore: number) => {
    if (riskScore <= 30) return "text-green-600";
    if (riskScore <= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getRiskLevel = (riskScore: number) => {
    if (riskScore <= 30) return "Low Risk";
    if (riskScore <= 60) return "Medium Risk";
    return "High Risk";
  };

  const getRiskDotColor = (riskScore: number) => {
    if (riskScore <= 30) return "bg-green-400";
    if (riskScore <= 60) return "bg-yellow-400";
    return "bg-red-400";
  };

  const userCountry = user?.country || 'IN';

  const formatDate = (date: any) => {
    try {
      if (!date) return 'N/A';
      const parsedDate = new Date(date);
      if (isNaN(parsedDate.getTime())) {
        return 'Invalid date';
      }
      return parsedDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return 'Invalid date';
    }
  };

  // Use isVerified and lastLogin from user object if available
  const isVerified = typeof user?.isVerified === 'boolean' ? user.isVerified : false;
  const lastLogin = user?.lastLogin;
  const riskLevel = typeof user?.riskLevel === 'string' ? user.riskLevel : 'Low';
  const location = typeof user?.country === 'string' ? user.country : 'Unknown';

  return (
    <section className="py-8 min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-end mb-4">
          <Button onClick={() => setShowHeatmap((v) => !v)} variant="outline">
            {showHeatmap ? "Back to Dashboard" : "View My Heatmap"}
          </Button>
        </div>
        {showHeatmap ? (
          <Heatmap />
        ) : (
          <>
            {/* Admin Access Banner - Only visible to admins */}
            {user?.isAdmin && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.05 }}
                className="mb-6"
              >
                <Card className="border-red-200 bg-gradient-to-r from-red-50 to-orange-50">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-red-100 rounded-full">
                          <Shield className="h-5 w-5 text-red-600" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-red-900">Administrator Access</h3>
                          <p className="text-sm text-red-700">You have admin privileges. Access the admin panel to manage users and system settings.</p>
                        </div>
                      </div>
                      <Link href="/admin">
                        <Button className="bg-red-600 hover:bg-red-700 text-white">
                          Open Admin Panel
                          <ExternalLink className="ml-2 h-4 w-4" />
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Welcome Header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="mb-8"
            >
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Welcome back, {typeof user?.name === 'string' ? user.name.split(' ')?.[0] || 'User' : 'User'}!
              </h1>
              <p className="text-gray-600">Here's your account overview and recent activity.</p>
            </motion.div>

            <div className="grid lg:grid-cols-3 gap-8">
              {/* Main Content */}
              <div className="lg:col-span-2 space-y-8">
                {/* Account Balance Cards */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.1 }}
                  className="grid md:grid-cols-2 gap-6"
                >
                  <Card className="bg-gradient-to-br from-primary to-blue-700 text-white">
                    <CardContent className="p-6">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <p className="text-blue-100 text-sm">Checking Account</p>
                          <p className="text-2xl font-bold">{formatAmountByCountry(12847.92, userCountry)}</p>
                        </div>
                        <CreditCard className="h-6 w-6 text-blue-200" />
                      </div>
                      <div className="flex items-center text-sm text-blue-100">
                        <TrendingUp className="mr-1 h-4 w-4" />
                        <span>+2.5% this month</span>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="banking-card">
                    <CardContent className="p-6">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <p className="text-gray-600 text-sm">Savings Account</p>
                          <p className="text-2xl font-bold text-gray-900">{formatAmountByCountry(45392.14, userCountry)}</p>
                        </div>
                        <PiggyBank className="h-6 w-6 text-green-500" />
                      </div>
                      <div className="flex items-center text-sm text-green-600">
                        <TrendingUp className="mr-1 h-4 w-4" />
                        <span>+$850 interest</span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Recent Transactions */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                >
                  <Card className="banking-card">
                    <CardHeader>
                      <div className="flex justify-between items-center">
                        <CardTitle className="text-lg font-semibold">Recent Transactions</CardTitle>
                        <Link href="/transactions">
                          <Button variant="ghost" size="sm" className="text-primary hover:text-primary/80">
                            View All
                            <ExternalLink className="ml-2 h-4 w-4" />
                          </Button>
                        </Link>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {recentTransactions.length > 0 ? (
                        <div className="space-y-4">
                          {recentTransactions.map((transaction: Transaction) => (
                            <div 
                              key={transaction.id || `transaction-${Math.random()}`}
                              className="flex items-center justify-between p-4 hover:bg-gray-50 rounded-lg transition-colors"
                            >
                              <div className="flex items-center space-x-3">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                  (typeof transaction.type === 'string' ? transaction.type : 'withdrawal') === 'deposit' ? 'bg-green-100' : 'bg-red-100'
                                }`}>
                                  {(typeof transaction.type === 'string' ? transaction.type : 'withdrawal') === 'deposit' ? (
                                    <ArrowDownLeft className="h-5 w-5 text-green-600" />
                                  ) : (
                                    <ArrowUpRight className="h-5 w-5 text-red-600" />
                                  )}
                                </div>
                                <div>
                                  <p className="font-medium text-gray-900">{typeof transaction.description === 'string' ? transaction.description : 'Transaction'}</p>
                                  <p className="text-sm text-gray-600">{transaction.createdAt ? formatDate(transaction.createdAt) : 'Unknown date'}</p>
                                </div>
                              </div>
                              <div className="text-right">
                                <p className={`font-semibold ${
                                  (typeof transaction.type === 'string' ? transaction.type : 'withdrawal') === 'deposit' ? 'text-green-600' : 'text-red-600'
                                }`}>
                                  {(typeof transaction.type === 'string' ? transaction.type : 'withdrawal') === 'deposit' ? '+' : '-'}{formatAmountByCountry(typeof transaction.amount === 'number' ? transaction.amount : 0, userCountry)}
                                </p>
                                <div className="flex items-center text-xs text-gray-500">
                                  <div className={`w-2 h-2 rounded-full mr-1 ${getRiskDotColor(typeof transaction.riskScore === 'number' ? transaction.riskScore : 0)}`}></div>
                                  {getRiskLevel(typeof transaction.riskScore === 'number' ? transaction.riskScore : 0)}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-8 text-gray-500">
                          <p>No transactions yet</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Quick Actions */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                >
                  <Card className="banking-card">
                    <CardHeader>
                      <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <Button
                          variant="outline"
                          className="p-4 h-auto flex-col space-y-2 hover:border-primary hover:bg-primary/5"
                          onClick={() => setIsTransferModalOpen(true)}
                        >
                          <Plus className="h-6 w-6 text-primary" />
                          <span className="text-sm font-medium">Transfer</span>
                        </Button>
                        
                        <Link href="/transactions">
                          <Button
                            variant="outline"
                            className="p-4 h-auto flex-col space-y-2 hover:border-primary hover:bg-primary/5 w-full"
                          >
                            <History className="h-6 w-6 text-primary" />
                            <span className="text-sm font-medium">History</span>
                          </Button>
                        </Link>
                        
                        <Button
                          variant="outline"
                          className="p-4 h-auto flex-col space-y-2 hover:border-primary hover:bg-primary/5"
                        >
                          <Settings className="h-6 w-6 text-primary" />
                          <span className="text-sm font-medium">Settings</span>
                        </Button>
                        
                        {user?.isAdmin && (
                          <Link href="/admin">
                            <Button
                              variant="outline"
                              className="p-4 h-auto flex-col space-y-2 hover:border-red-500 hover:bg-red-50 border-red-200 bg-red-50/50 w-full"
                            >
                              <Shield className="h-6 w-6 text-red-600" />
                              <span className="text-sm font-medium text-red-700">Admin Panel</span>
                            </Button>
                          </Link>
                        )}

                        <Button
                          variant="outline"
                          className="p-4 h-auto flex-col space-y-2 hover:border-primary hover:bg-primary/5"
                        >
                          <Headphones className="h-6 w-6 text-primary" />
                          <span className="text-sm font-medium">Support</span>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </div>

              {/* Sidebar */}
              <div className="space-y-6">
                {/* Security Status */}
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.4 }}
                >
                  <Card className="banking-card">
                    <CardHeader>
                      <CardTitle className="text-lg font-semibold flex items-center">
                        <Shield className="mr-2 h-5 w-5 text-primary" />
                        Security Status
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Risk Level</span>
                          <Badge variant="outline" className={riskLevel === 'Low' ? 'text-green-600 border-green-200 bg-green-50' : riskLevel === 'Medium' ? 'text-yellow-600 border-yellow-200 bg-yellow-50' : 'text-red-600 border-red-200 bg-red-50'}>
                            <div className={`w-2 h-2 rounded-full mr-2 ${riskLevel === 'Low' ? 'bg-green-400' : riskLevel === 'Medium' ? 'bg-yellow-400' : 'bg-red-400'}`}></div>
                            {riskLevel}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Device Trust</span>
                          <div className={`flex items-center text-sm ${isVerified ? 'text-green-600' : 'text-red-600'}`}>
                            <CheckCircle className="mr-1 h-4 w-4" />
                            {isVerified ? 'Verified' : 'Unverified'}
                          </div>
                        </div>
                        <div className="pt-3 border-t border-gray-100">
                          <div className="text-xs text-gray-500 space-y-1">
                            <p>Last Login: {lastLogin ? new Date(lastLogin).toLocaleString() : 'Unknown'}</p>
                            <p>Location: {location}</p>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Account Summary */}
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.5 }}
                >
                  <Card className="banking-card">
                    <CardHeader>
                      <CardTitle className="text-lg font-semibold">Account Summary</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Total Balance</span>
                          <span className="font-medium text-gray-900">{formatAmountByCountry(58240.06, userCountry)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Available Credit</span>
                          <span className="font-medium text-gray-900">{formatAmountByCountry(15000.00, userCountry)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Monthly Spending</span>
                          <span className="font-medium text-gray-900">{formatAmountByCountry(2847.32, userCountry)}</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Notifications */}
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.6 }}
                >
                  <Card className="banking-card">
                    <CardHeader>
                      <CardTitle className="text-lg font-semibold">Recent Alerts</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex items-start space-x-2">
                            <CheckCircle className="text-green-500 text-sm mt-0.5 h-4 w-4" />
                            <div>
                              <p className="text-sm font-medium text-green-800">Transaction Approved</p>
                              <p className="text-xs text-green-600">Recent purchase verified</p>
                            </div>
                          </div>
                        </div>
                        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <div className="flex items-start space-x-2">
                            <Shield className="text-blue-500 text-sm mt-0.5 h-4 w-4" />
                            <div>
                              <p className="text-sm font-medium text-blue-800">New Device Login</p>
                              <p className="text-xs text-blue-600">Verified from your location</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
                <DeviceManagement />
              </div>
            </div>
          </>
        )}
      </div>

      <TransferModal 
        isOpen={isTransferModalOpen} 
        onClose={() => setIsTransferModalOpen(false)}
      />
    </section>
  );
}
