import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginSchema, type LoginInput } from "@shared/schema";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { motion } from "framer-motion";
import { Link } from "wouter";
import { ArrowLeft, Mail } from "lucide-react";
import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";

export default function Login() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { login, user } = useAuth();

  // Step 1: Identifier input
  const [identifier, setIdentifier] = useState("");
  const [identifierError, setIdentifierError] = useState("");

  // Step 2: Behavioral challenge
  const [challengeType, setChallengeType] = useState<"typing" | "mouse" | "touch">();
  const [challengeData, setChallengeData] = useState<any>(null);
  const [challengeComplete, setChallengeComplete] = useState(false);

  // Step 3: Background metrics
  const [metrics, setMetrics] = useState<{ ip: string; geo: { latitude: number | null; longitude: number | null; accuracy: number | null; fallback: boolean }; device: { browser?: string } }>({ ip: "", geo: { latitude: null, longitude: null, accuracy: null, fallback: true }, device: {} });
  const [metricsPreviewOpen, setMetricsPreviewOpen] = useState(false);

  // Risk and feedback state
  const [risk, setRisk] = useState<string | null>(null);
  const [riskReasons, setRiskReasons] = useState<string[]>([]);
  const [showRiskModal, setShowRiskModal] = useState(false);

  // Ensure modal is only shown for medium/high risk
  useEffect(() => {
    if (risk === "low") {
      setShowRiskModal(false);
    } else if (risk === "medium" || risk === "high") {
      setShowRiskModal(true);
    }
  }, [risk]);
  const [feedbackSent, setFeedbackSent] = useState(false);

  // Add new state for step-up verification
  const [stepupOptions, setStepupOptions] = useState<string[]>([]);
  const [stepupInProgress, setStepupInProgress] = useState<string | null>(null);
  const [stepupError, setStepupError] = useState<string | null>(null);
  const [trustedDeviceEligible, setTrustedDeviceEligible] = useState<boolean>(false);

  // Security question state
  const [showSecurityQuestion, setShowSecurityQuestion] = useState(false);
  const [securityQuestion, setSecurityQuestion] = useState("");
  const [securityAnswer, setSecurityAnswer] = useState("");

  // Prime CSRF cookie on mount with a safe GET so POSTs have matching header
  useEffect(() => {
    (async () => {
      try {
        await apiRequest("GET", "/health");
      } catch (_) {
        // No-op: this is best-effort just to set csrf_token cookie
      }
    })();
  }, []);

  // If already authenticated, redirect away from /login
  useEffect(() => {
    if (user) {
      setLocation("/dashboard");
    }
  }, [user, setLocation]);

  // Randomize challenge type on mount
  useEffect(() => {
    const isMobile = /Mobi|Android/i.test(navigator.userAgent);
    const types = isMobile ? ["typing", "touch"] : ["typing", "mouse"];
  setChallengeType(types[Math.floor(Math.random() * types.length)] as "typing" | "mouse" | "touch");
  }, []);

  // Collect background metrics (IP, geo, device, etc.)
  useEffect(() => {
    async function collectMetrics() {
      // Public IP via backend (avoids third-party rate limits)
      let ip = "";
      try {
        const ipRes = await fetch(`/api/util/ip`, { credentials: "include" });
        if (ipRes.ok) {
          ip = (await ipRes.json()).ip || "";
        }
      } catch {}
      // Geolocation
  let geo: { latitude: number | null; longitude: number | null; accuracy: number | null; fallback: boolean } = { latitude: null, longitude: null, accuracy: null, fallback: true };
      if (navigator.geolocation) {
        await new Promise((resolve) => {
          navigator.geolocation.getCurrentPosition(
            (pos) => {
              geo = {
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
                accuracy: pos.coords.accuracy,
                fallback: false,
              };
              resolve(null);
            },
            () => resolve(null),
            { enableHighAccuracy: true, timeout: 5000 }
          );
        });
      }
      // Device info
      const device = {
        browser: navigator.userAgent,
        os: navigator.platform,
        screen: `${window.screen.width}x${window.screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        language: navigator.language,
      };
      setMetrics((m: any) => ({ ...m, ip, geo, device }));
    }
    collectMetrics();
  }, []);

  // Step 4: Preview section (blurred)
  // ... will be rendered below form

  // Step 5: Submission
  const loginMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        identifier,
        behavioral_challenge: {
          type: challengeType,
          data: challengeData,
        },
        metrics,
      };
      const response = await apiRequest("POST", "/api/auth/login", payload);
      // Log full response for debugging
      const data = await response.json();
      if (import.meta.env.DEV) {
        console.log("[LOGIN API RESPONSE]", data);
      }
      return data;
    },
    onSuccess: (data) => {
      // Fallback if risk is missing
      const riskLevel = data.risk || "unknown";
      if (import.meta.env.DEV) {
        console.log("[LOGIN onSuccess] risk:", riskLevel, "data:", data);
      }
      if (riskLevel === "low") {
        login(data.user);
        setRisk(null);
        setRiskReasons([]);
        setShowRiskModal(false);
        toast({
          title: "Welcome back!",
          description: "You have successfully signed in.",
        });
        setLocation("/dashboard");
      } else if (riskLevel === "medium") {
        setLocation(`/additional-verification?identifier=${encodeURIComponent(identifier)}`);
      } else if (riskLevel === "high") {
        setRisk(riskLevel);
        setRiskReasons(data.reasons || []);
        setShowRiskModal(true);
        toast({
          title: "Login Blocked: High Risk",
          description: (data.reasons && data.reasons.length > 0)
            ? data.reasons.join("; ")
            : "Your login was blocked for security reasons.",
          variant: "destructive",
        });
      } else {
        // Unknown risk, treat as failed
        setRisk(riskLevel);
        setRiskReasons(data.reasons || ["Unknown risk level"]);
        setShowRiskModal(true);
        toast({
          title: "Login Failed",
          description: (data.reasons && data.reasons.length > 0)
            ? data.reasons.join("; ")
            : "Unknown risk level.",
          variant: "destructive",
        });
      }
    },
    onError: (error: any) => {
      // Only block if risk is high or status is 403
      const status = error?.status;
      const riskLevel = error?.detail?.risk || (status === 403 ? "high" : "unknown");
      const reasons = error?.detail?.reasons || [error?.detail?.message || error?.message || "Unknown error"];
      if (import.meta.env.DEV) {
        console.error("[LOGIN onError]", error);
      }
      setRisk(riskLevel);
      setRiskReasons(reasons);
      setShowRiskModal(true);
      toast({
        title: riskLevel === "high" ? "Login Blocked: High Risk" : "Login Failed",
        description: reasons.join("; "),
        variant: "destructive",
      });
    },
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIdentifierError("");
    if (!identifier) {
      setIdentifierError("Please enter your email, username, or phone number.");
      return;
    }
    if (!challengeComplete) {
      toast({ title: "Complete the behavioral challenge first." });
      return;
    }
    loginMutation.mutate();
  };

  // Feedback handler
  const sendFeedback = async (correct: boolean) => {
    await apiRequest("POST", "/api/auth/feedback", { identifier, risk, correct, reasons: riskReasons, metrics });
    setFeedbackSent(true);
  };

  // Add BehavioralChallenge component
  function BehavioralChallenge({ type, onComplete }: { type: "typing" | "mouse" | "touch", onComplete: (data: any) => void }) {
    // Typing challenge state
    const TYPING_SAMPLE = "The quick brown fox jumps over the lazy dog.";
    const [typed, setTyped] = useState("");
    const [startTime, setStartTime] = useState<number | null>(null);
    const [keystrokes, setKeystrokes] = useState<number[]>([]);
    const [backspaces, setBackspaces] = useState(0);
    const [complete, setComplete] = useState(false);

    // Mouse challenge state
    const [mousePath, setMousePath] = useState<{x: number, y: number, t: number}[]>([]);
    const [mouseClicks, setMouseClicks] = useState(0);
    const [mouseStart, setMouseStart] = useState<number | null>(null);

    // Touch challenge state
    const [touchPath, setTouchPath] = useState<{x: number, y: number, t: number}[]>([]);
    const [touchStart, setTouchStart] = useState<number | null>(null);

    // Typing challenge logic
    useEffect(() => {
      if (type === "typing" && typed === TYPING_SAMPLE) {
        setComplete(true);
        const duration = (Date.now() - (startTime || Date.now())) / 1000;
        const wpm = (TYPING_SAMPLE.split(" ").length / duration) * 60;
        const errorRate =
          typed.length === TYPING_SAMPLE.length
            ? Array.from(typed).filter((c, i) => c !== TYPING_SAMPLE[i]).length / TYPING_SAMPLE.length
            : 1;
        onComplete({
          wpm,
          errorRate,
          keystrokeTimings: keystrokes,
          backspaces,
          duration,
        });
      }
    }, [typed]);
    // Mouse challenge logic
    useEffect(() => {
      if (type === "mouse" && mousePath.length > 50 && mouseClicks > 2) {
        setComplete(true);
        const duration = (Date.now() - (mouseStart || Date.now())) / 1000;
        onComplete({
          path: mousePath,
          clicks: mouseClicks,
          duration,
        });
      }
    }, [mousePath, mouseClicks]);

    // Touch challenge logic
    useEffect(() => {
      if (type === "touch" && touchPath.length > 30) {
        setComplete(true);
        const duration = (Date.now() - (touchStart || Date.now())) / 1000;
        onComplete({
          path: touchPath,
          duration,
        });
      }
    }, [touchPath]);

    if (type === "typing") {
      return (
        <div className="mb-2">
          <div className="text-xs text-gray-500 mb-1">Type the sentence below as quickly and accurately as you can:</div>
          <div className="p-2 bg-gray-100 rounded mb-2 text-xs">{TYPING_SAMPLE}</div>
          <input
            className="w-full border rounded p-2 text-sm"
            value={typed}
            onChange={e => {
              if (!startTime) setStartTime(Date.now());
              setTyped(e.target.value);
              setKeystrokes(ks => [...ks, Date.now() - (startTime || Date.now())]);
            }}
            onKeyDown={e => {
              if (e.key === "Backspace") setBackspaces(b => b + 1);
            }}
            disabled={complete}
          />
          {complete && <div className="text-green-600 text-xs mt-1">Challenge complete!</div>}
        </div>
      );
    }
    if (type === "mouse") {
      return (
        <div className="mb-2">
          <div className="text-xs text-gray-500 mb-1">Move your mouse in this area and click at least 3 times:</div>
          <div
            className="w-full h-24 border-2 border-dashed rounded bg-gray-50 relative"
            onMouseMove={e => {
              if (!mouseStart) setMouseStart(Date.now());
              setMousePath(path => [...path, { x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY, t: Date.now() - (mouseStart || Date.now()) }]);
            }}
            onClick={() => setMouseClicks(c => c + 1)}
          >
            <div className="absolute bottom-1 right-2 text-xs text-gray-400">Moves: {mousePath.length}, Clicks: {mouseClicks}</div>
          </div>
          {complete && <div className="text-green-600 text-xs mt-1">Challenge complete!</div>}
        </div>
      );
    }
    if (type === "touch") {
      return (
        <div className="mb-2">
          <div className="text-xs text-gray-500 mb-1">Swipe or tap in this area:</div>
          <div
            className="w-full h-24 border-2 border-dashed rounded bg-gray-50 relative"
            onTouchStart={e => {
              if (!touchStart) setTouchStart(Date.now());
              const t = Date.now() - (touchStart || Date.now());
              setTouchPath(path => [...path, { x: e.touches[0].clientX, y: e.touches[0].clientY, t }]);
            }}
            onTouchMove={e => {
              const t = Date.now() - (touchStart || Date.now());
              setTouchPath(path => [...path, { x: e.touches[0].clientX, y: e.touches[0].clientY, t }]);
            }}
          >
            <div className="absolute bottom-1 right-2 text-xs text-gray-400">Touches: {touchPath.length}</div>
          </div>
          {complete && <div className="text-green-600 text-xs mt-1">Challenge complete!</div>}
        </div>
      );
    }
    return null;
  }

  // Add helper for base64url encoding
  function bufferToBase64url(buffer: ArrayBuffer) {
  return btoa(String.fromCharCode(...Array.from(new Uint8Array(buffer))))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  }

  return (
    <section className="py-20 min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md mx-auto px-4 w-full">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="banking-card">
            <CardHeader className="text-center">
              <div className="flex items-center justify-between mb-4">
                <Link href="/">
                  <Button variant="ghost" size="sm">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back
                  </Button>
                </Link>
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                  <Mail className="h-6 w-6 text-primary" />
                </div>
              </div>
              <CardTitle className="text-2xl font-bold text-gray-900 mb-2">
                Welcome Back
              </CardTitle>
              <p className="text-gray-600">Sign in to your secure banking account</p>
            </CardHeader>
            <CardContent>
              <form onSubmit={onSubmit} className="space-y-6">
                <div>
                  <Label htmlFor="identifier" className="block text-sm font-medium text-gray-700 mb-2">
                    Email, Username, or Phone
                  </Label>
                  <Input
                    id="identifier"
                    value={identifier}
                    onChange={e => setIdentifier(e.target.value)}
                    placeholder="Enter your email, username, or phone"
                    className="w-full"
                  />
                  {identifierError && (
                    <p className="text-sm text-red-600 mt-1">{identifierError}</p>
                  )}
                </div>
                {/* Behavioral Challenge */}
                <BehavioralChallenge
                  type={challengeType!}
                  onComplete={data => {
                    setChallengeData(data);
                    setChallengeComplete(true);
                  }}
                />
                <Button
                  type="submit"
                  className="w-full banking-button-primary"
                  disabled={loginMutation.isPending}
                >
                  {loginMutation.isPending ? "Signing you in..." : "Sign In"}
                </Button>
              </form>
              {/* Metrics Preview Section (blurred) */}
              <div className="mt-6">
                <button
                  className="text-xs text-primary underline mb-2"
                  onClick={() => setMetricsPreviewOpen(v => !v)}
                  type="button"
                >
                  {metricsPreviewOpen ? "Hide" : "See why this is collected"}
                </button>
                {metricsPreviewOpen && (
                  <div className="p-4 bg-gray-100 rounded-lg text-xs">
                    <div className="mb-2 font-medium">Collected Metrics (partially blurred):</div>
                    <div className="flex flex-col gap-1">
                      <span>IP: <span className="blur-sm">{metrics.ip?.slice(0, 6)}</span>•••</span>
                      <span>Device: <span className="blur-sm">{metrics.device?.browser?.slice(0, 10)}</span>•••</span>
                      <span>Geo: <span className="blur-sm">{metrics.geo?.latitude}</span>, <span className="blur-sm">{metrics.geo?.longitude}</span></span>
                      {/* Add more fields as needed, blur most values */}
                    </div>
                    <div className="mt-2 text-gray-500">We collect minimal info to verify it's really you and keep your account safe. Data is encrypted and never shared.</div>
                  </div>
                )}
              </div>
              <div className="mt-6 text-center">
                <p className="text-sm text-gray-600">
                  Don't have an account?{" "}
                  <Link href="/register" className="text-primary hover:text-primary/80 font-medium">
                    Sign up
                  </Link>
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
      <Dialog open={showRiskModal} onOpenChange={setShowRiskModal}>
        <DialogContent>
          <DialogTitle>
            {risk === "high" ? "High Risk Login Blocked" : risk === "medium" ? "Additional Verification Required" : "Login Risk"}
          </DialogTitle>
          <DialogDescription>
            {riskReasons.length > 0 ? (
              <ul className="list-disc pl-5 text-sm text-gray-700">
                {riskReasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            ) : (
              <div className="text-sm text-gray-700">No specific reasons provided. Please contact support.</div>
            )}
            {risk === "medium" && (
              <div className="mt-4 flex flex-col gap-3">
                {stepupError && <div className="text-red-600 text-xs">{stepupError}</div>}
                {stepupOptions.includes("webauthn") && window.PublicKeyCredential && (
                  <Button disabled={!!stepupInProgress} onClick={async () => {
                    setStepupInProgress("webauthn"); setStepupError(null);
                    try {
                      // ...existing code...
                    } catch (e: any) {
                      setStepupError(e.message || "WebAuthn failed");
                    }
                    setStepupInProgress(null);
                  }}>Use Biometrics (WebAuthn)</Button>
                )}
                {stepupOptions.includes("behavioral") && (
                  <Button disabled={!!stepupInProgress} onClick={async () => {
                    setStepupInProgress("behavioral"); setStepupError(null);
                    try {
                      // ...existing code...
                    } catch (e: any) { setStepupError(e.message || "Behavioral verification failed"); }
                    setStepupInProgress(null);
                  }}>Retry Behavioral Challenge</Button>
                )}
                {stepupOptions.includes("trusted_device") && trustedDeviceEligible && (
                  <Button disabled={!!stepupInProgress} onClick={async () => {
                    setStepupInProgress("trusted_device"); setStepupError(null);
                    try {
                      // ...existing code...
                    } catch (e: any) { setStepupError(e.message || "Trusted device verification failed"); }
                    setStepupInProgress(null);
                  }}>Confirm Trusted Device</Button>
                )}
                {stepupOptions.includes("magic_link") && (
                  <Button disabled={!!stepupInProgress} onClick={async () => {
                    setStepupInProgress("magic_link"); setStepupError(null);
                    try {
                      // ...existing code...
                    } catch (e: any) { setStepupError(e.message || "Magic link failed"); }
                    setStepupInProgress(null);
                  }}>Send me a magic link</Button>
                )}
                {/* Security Question Modal */}
                <Button disabled={!!stepupInProgress} onClick={async () => {
                  setStepupInProgress("context_question");
                  setStepupError(null);
                  // Fetch question from backend
                  const res = await apiRequest("POST", "/api/auth/context-question", { identifier });
                  const data = await res.json();
                  setSecurityQuestion(data.question);
                  setShowSecurityQuestion(true);
                  setStepupInProgress(null);
                }}>Answer Security Question</Button>
                {/* Ambient Verification Modal */}
                <Button disabled={!!stepupInProgress} onClick={async () => {
                  setStepupInProgress("ambient_auth");
                  setStepupError(null);
                  // Collect ambient data
                  const ambient = {
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    screen: `${window.screen.width}x${window.screen.height}`,
                    orientation: window.screen.orientation?.type || "unknown",
                    language: navigator.language,
                  };
                  // Send to backend
                  const res = await apiRequest("POST", "/api/auth/ambient-verify", { identifier, ambient });
                  const data = await res.json();
                  if (data.success) {
                    toast({ title: "Environment Verified", description: "Ambient authentication successful!" });
                    loginMutation.mutate();
                  } else {
                    setStepupError(data.message || "Ambient authentication failed");
                  }
                  setStepupInProgress(null);
                }}>Verify Environment</Button>
                {/* Security Question Modal UI */}
                {showSecurityQuestion && (
                  <div className="p-4 bg-white rounded shadow mt-2">
                    <div className="mb-2 font-bold">Security Question</div>
                    <div className="mb-2">{securityQuestion}</div>
                    <input
                      type="text"
                      className="border rounded p-2 w-full mb-2"
                      value={securityAnswer}
                      onChange={e => setSecurityAnswer(e.target.value)}
                      placeholder="Your answer"
                    />
                    <Button onClick={async () => {
                      setStepupError(null);
                      const res = await apiRequest("POST", "/api/auth/context-answer", { identifier, answer: securityAnswer });
                      const data = await res.json();
                      if (data.success) {
                        toast({ title: "Verified", description: "Security question answered correctly!" });
                        setShowSecurityQuestion(false);
                        loginMutation.mutate();
                      } else {
                        setStepupError(data.message || "Incorrect answer");
                      }
                    }}>Submit Answer</Button>
                    <Button variant="secondary" onClick={() => setShowSecurityQuestion(false)}>Cancel</Button>
                    {stepupError && <div className="text-red-600 text-xs mt-2">{stepupError}</div>}
                  </div>
                )}
              </div>
            )}
            {risk === "high" && <div className="mt-4 text-red-700">Your login was blocked for security reasons.</div>}
          </DialogDescription>
          <div className="flex gap-2 justify-end">
            <button className="btn btn-secondary" onClick={() => setShowRiskModal(false)}>Close</button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}
