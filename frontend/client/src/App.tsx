import { Switch, Route, Router } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import NotFound from "@/pages/not-found";
import Landing from "@/pages/Landing";
import Register from "@/pages/Register";
import VerifyEmail from "@/pages/VerifyEmail";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import Transactions from "@/pages/Transactions";
import Admin from "@/pages/Admin";
import Login from "@/pages/Login";
import HealthCheckPage from "@/pages/HealthCheck";
import AdditionalVerification from "@/pages/AdditionalVerification";
import Navbar from "@/components/Navbar";
import { AuthProvider, withAuth, withAdminAuth, withGuest } from "@/hooks/use-auth";

function AppRouter() {
  return (
    <>
      <Navbar />
      <main className="pt-16 min-h-screen">
        <Switch>
          <Route path="/" component={Landing} />
          <Route path="/register" component={withGuest(Register)} />
          <Route path="/verify-email" component={VerifyEmail} />
          <Route path="/onboarding" component={withAuth(Onboarding)} />
          <Route path="/login" component={withGuest(Login)} />
          <Route path="/additional-verification" component={withGuest(AdditionalVerification)} />
          <Route path="/dashboard" component={withAuth(Dashboard)} />
          <Route path="/transactions" component={withAuth(Transactions)} />
          <Route path="/admin" component={withAdminAuth(Admin)} />
          <Route path="/health" component={HealthCheckPage} />
          <Route component={NotFound} />
        </Switch>
      </main>
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
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
    </ErrorBoundary>
  );
}

export default App;
