import { Switch, Route, Router } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import Landing from "@/pages/Landing";
import Register from "@/pages/Register";
import VerifyEmail from "@/pages/VerifyEmail";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import Transactions from "@/pages/Transactions";
import Admin from "@/pages/Admin";
import Login from "@/pages/Login";
import Navbar from "@/components/Navbar";
import { AuthProvider, withAuth, withAdminAuth } from "@/hooks/use-auth";

function AppRouter() {
  return (
    <>
      <Navbar />
      <main className="pt-16 min-h-screen">
        <Switch>
          <Route path="/" component={Landing} />
          <Route path="/register" component={Register} />
          <Route path="/verify-email" component={VerifyEmail} />
          <Route path="/onboarding" component={Onboarding} />
          <Route path="/login" component={Login} />
          <Route path="/dashboard" component={withAuth(Dashboard)} />
          <Route path="/transactions" component={withAuth(Transactions)} />
          <Route path="/admin" component={withAdminAuth(Admin)} />
          <Route component={NotFound} />
        </Switch>
      </main>
    </>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AuthProvider>
          <Router base="/">
            <Toaster />
            <AppRouter />
          </Router>
        </AuthProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
