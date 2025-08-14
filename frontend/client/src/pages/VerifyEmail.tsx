import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocation } from "wouter";
import { motion } from "framer-motion";
import { Mail, CheckCircle, RefreshCw } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

export default function VerifyEmail() {
  const [, setLocation] = useLocation();
  const [email, setEmail] = useState<string>("");
  const { toast } = useToast();
  const [tokenParam, setTokenParam] = useState<string | null>(null);

  useEffect(() => {
    const url = new URL(window.location.href);
    const t = url.searchParams.get("token");
    if (t) setTokenParam(t);
    const pendingEmail = localStorage.getItem("securebank_pending_email");
    if (pendingEmail) setEmail(pendingEmail);
  }, [setLocation]);

  const verifyMutation = useMutation({
    mutationFn: async () => {
      if (tokenParam) {
        const res = await apiRequest("GET", `/api/auth/verify?token=${encodeURIComponent(tokenParam)}`);
        return await res.json();
      }
  const response = await apiRequest("POST", "/api/auth/verify-email", { identifier: email });
      return await response.json();
    },
    onSuccess: (data: any) => {
      if (tokenParam) {
        toast({ title: "Email Verified!", description: "Verification successful." });
        if (data?.token) {
          try { localStorage.setItem("securebank_token", data.token); } catch {}
        }
        setLocation("/onboarding");
        return;
      }
      // Resend path: don't navigate; just notify
      toast({ title: "Verification email sent", description: "Please check your inbox and click the link." });
    },
    onError: (error: any) => {
      toast({
        title: "Verification Failed",
        description: error.message || "Something went wrong",
        variant: "destructive",
      });
    },
  });

  const handleVerify = () => {
    verifyMutation.mutate();
  };

  return (
    <section className="py-20 min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="banking-card text-center">
            <CardHeader>
              <div className="flex items-center justify-center mb-4">
                <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center mr-2">
                  <span className="text-gray-500 text-xs font-bold">1</span>
                </div>
                <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center mr-2">
                  <span className="text-white text-xs font-bold">2</span>
                </div>
                <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center">
                  <span className="text-gray-500 text-xs font-bold">3</span>
                </div>
              </div>
              
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6"
              >
                <Mail className="h-8 w-8 text-primary" />
              </motion.div>
              
              <CardTitle className="text-2xl font-bold text-gray-900 mb-4">
                Check Your Email
              </CardTitle>
              
              <p className="text-gray-600 mb-8">
                We've sent a verification link to{" "}
                <span className="font-medium text-gray-900">{email}</span>.
                Click the link to complete your registration.
              </p>
            </CardHeader>
            
            <CardContent className="space-y-4">
      <Button 
                onClick={handleVerify}
                className="w-full banking-button-primary"
                disabled={verifyMutation.isPending}
              >
                {verifyMutation.isPending ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />
        Verify and Continue
                  </>
                )}
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full banking-button-secondary"
                onClick={() => {
                  toast({
                    title: "Verification email sent",
                    description: "Please check your inbox.",
                  });
                }}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Resend Verification Email
              </Button>
              
              <div className="mt-6 text-center">
                <p className="text-sm text-gray-500">
                  Didn't receive the email? Check your spam folder or{" "}
                  <button 
                    onClick={() => setLocation("/register")}
                    className="text-primary hover:text-primary/80 underline"
                  >
                    try a different email address
                  </button>
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </section>
  );
}
