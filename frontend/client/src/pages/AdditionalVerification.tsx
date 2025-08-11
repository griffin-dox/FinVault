import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

export default function AdditionalVerification({ identifier }: { identifier: string }) {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [ambientResult, setAmbientResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch security question on mount
  useState(() => {
    fetch("/api/auth/context-question", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier })
    })
      .then(res => res.json())
      .then(data => setQuestion(data.question));
  });

  const submitAnswer = async () => {
    setError(null);
    const res = await fetch("/api/auth/context-answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, answer })
    });
    const data = await res.json();
    if (data.success && data.risk === "low") {
      toast({ title: "Verified", description: "Security question answered correctly!" });
      setLocation("/dashboard");
    } else if (data.success) {
      toast({ title: "Verified", description: "Verification passed, but risk is not low. Access denied." });
      setError("Access denied: risk is not low.");
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
    const res = await fetch("/api/auth/ambient-verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, ambient })
    });
    const data = await res.json();
    if (data.success && data.risk === "low") {
      setAmbientResult("Ambient authentication successful!");
      toast({ title: "Environment Verified", description: "Ambient authentication successful!" });
      setLocation("/dashboard");
    } else if (data.success) {
      toast({ title: "Verified", description: "Verification passed, but risk is not low. Access denied." });
      setError("Access denied: risk is not low.");
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
