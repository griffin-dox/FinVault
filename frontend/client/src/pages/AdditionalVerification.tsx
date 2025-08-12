import { useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { apiRequest } from "@/lib/queryClient";

function useQueryParam(name: string): string | null {
  return useMemo(() => {
    if (typeof window === "undefined") return null;
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
  }, [name]);
}

export default function AdditionalVerification() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { login } = useAuth();
  const identifier = useQueryParam("identifier") || "";
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [ambientResult, setAmbientResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch security question on mount
  useEffect(() => {
    if (!identifier) return;
    apiRequest("POST", "/api/auth/context-question", { identifier })
      .then(res => res.json())
      .then(data => setQuestion(data.question));
  }, [identifier]);

  const submitAnswer = async () => {
    setError(null);
  const res = await apiRequest("POST", "/api/auth/context-answer", { identifier, answer });
    const data = await res.json();
    if (data.success) {
      if (data.user) {
        try { login({ ...data.user, token: data.token }); } catch {}
      }
      toast({ title: "Verified", description: "Security question answered correctly!" });
      setLocation("/dashboard");
    } else {
      setError(data.message || "Incorrect answer");
    }
  };

  const verifyAmbient = async () => {
    setError(null);
    const ambient = {
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      screen: `${window.screen.width}x${window.screen.height}`,
      orientation: window.screen.orientation?.type || "unknown",
      language: navigator.language,
    };
  const res = await apiRequest("POST", "/api/auth/ambient-verify", { identifier, ambient });
    const data = await res.json();
    if (data.success) {
      if (data.user) {
        try { login({ ...data.user, token: data.token }); } catch {}
      }
      setAmbientResult("Ambient authentication successful!");
      toast({ title: "Environment Verified", description: "Ambient authentication successful!" });
      setLocation("/dashboard");
    } else {
      setError(data.message || "Ambient authentication failed");
    }
  };

  return (
    <section className="py-20 min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md mx-auto px-4 w-full">
        <div className="bg-white rounded shadow p-6">
          <h2 className="text-xl font-bold mb-4">Additional Verification Required</h2>
          <div className="mb-6">
            <div className="font-medium mb-2">Security Question</div>
            <div className="mb-2">{question}</div>
            <input
              type="text"
              className="border rounded p-2 w-full mb-2"
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              placeholder="Your answer"
            />
            <Button className="w-full mb-2" onClick={submitAnswer}>Submit Answer</Button>
          </div>
          <div className="mb-6">
            <div className="font-medium mb-2">Ambient Authentication</div>
            <Button className="w-full" onClick={verifyAmbient}>Verify Environment</Button>
            {ambientResult && <div className="text-green-600 text-xs mt-2">{ambientResult}</div>}
          </div>
          {error && <div className="text-red-600 text-xs mt-2">{error}</div>}
        </div>
      </div>
    </section>
  );
}
