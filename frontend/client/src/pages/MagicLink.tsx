import { useEffect } from "react";
import { useLocation } from "wouter";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

export default function MagicLink() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  useEffect(() => {
    const url = new URL(window.location.href);
    const token = url.searchParams.get("token");
    if (!token) {
      setLocation("/login");
      return;
    }
    (async () => {
      try {
        const res = await apiRequest("GET", `/api/auth/magic-link/verify?token=${encodeURIComponent(token)}`);
        const data = await res.json();
        if (data?.token) {
          try { localStorage.setItem("securebank_token", data.token); } catch {}
        }
        toast({ title: "Magic link verified", description: "You're now logged in." });
        setLocation("/dashboard");
      } catch (e: any) {
        toast({ title: "Magic link failed", description: e?.message || "Invalid or expired link", variant: "destructive" });
        setLocation("/login");
      }
    })();
  }, [setLocation, toast]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center text-gray-700">Verifying magic link…</div>
    </div>
  );
}
