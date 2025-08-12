import { useEffect, useRef } from 'react';

function getCsrfToken(): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const part of cookies) {
    const [rawKey, ...rest] = part.trim().split('=');
    const key = decodeURIComponent(rawKey || '');
    if (key === 'csrf_token') {
      return decodeURIComponent(rest.join('=') || '');
    }
  }
  return undefined;
}

type Telemetry = {
  device?: Record<string, any>;
  geo?: { latitude?: number; longitude?: number; fallback?: boolean };
  ip?: string;
  idle_jitter_ms?: number;
  pointer_speed_std?: number;
  nav_bf_usage?: number;
  scroll_max_pct?: number;
  dwell_ms?: number;
  replay_nonce?: string;
};

type Options = {
  sessionId: string;
  userId: number;
  intervalMs?: number; // batch interval, default 8000
  endpoint?: string; // default /api/session/telemetry
  statusEndpoint?: string; // default /api/session/status
  onRiskChange?: (level: 'low' | 'medium' | 'high', score: number) => void;
};

export function useSessionTelemetry(opts: Options) {
  const { sessionId, userId, intervalMs = 8000, endpoint = '/api/session/telemetry', statusEndpoint = '/api/session/status', onRiskChange } = opts;
  const bufferRef = useRef<Telemetry[]>([]);
  const lastMouseTs = useRef<number>(0);
  const lastPos = useRef<{ x: number; y: number } | null>(null);
  const bfCountRef = useRef(0);

  useEffect(() => {
    // Mouse speed sampling
    const onMove = (e: MouseEvent) => {
      const now = performance.now();
      if (lastMouseTs.current === 0) {
        lastMouseTs.current = now;
        lastPos.current = { x: e.clientX, y: e.clientY };
        return;
      }
      const dt = now - lastMouseTs.current;
      if (dt < 500) return; // throttle ~2Hz
      const prev = lastPos.current;
      const dx = prev ? Math.hypot(e.clientX - prev.x, e.clientY - prev.y) : 0;
      const speed = dx / dt; // px/ms
      const prevStd = bufferRef.current.at(-1)?.pointer_speed_std ?? 0;
      const newStd = Math.max(prevStd * 0.8 + Math.abs(speed) * 0.2, 0);
      bufferRef.current.push({ pointer_speed_std: newStd });
      if (bufferRef.current.length > 100) bufferRef.current.shift();
      lastMouseTs.current = now;
      lastPos.current = { x: e.clientX, y: e.clientY };
    };

    const onPopState = () => {
      bfCountRef.current += 1;
      bufferRef.current.push({ nav_bf_usage: bfCountRef.current });
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('popstate', onPopState);
    // Scroll depth tracking
    const onScroll = () => {
      const doc = document.documentElement;
      const maxScroll = doc.scrollHeight - doc.clientHeight;
      const pct = maxScroll > 0 ? (doc.scrollTop / maxScroll) * 100 : 0;
      const prev = bufferRef.current.at(-1)?.scroll_max_pct ?? 0;
      bufferRef.current.push({ scroll_max_pct: Math.max(prev, pct) });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    // Dwell time tracking
    const start = performance.now();
    const dwellTimer = window.setInterval(() => {
      const dwell = performance.now() - start;
      bufferRef.current.push({ dwell_ms: dwell });
      if (bufferRef.current.length > 100) bufferRef.current.shift();
    }, 3000);
    let idleTimer: number | undefined;

    // Idle jitter (very rough)
    const idleLoop = () => {
      const jitter = Math.random() * 5000; // placeholder variability
      bufferRef.current.push({ idle_jitter_ms: jitter });
      idleTimer = window.setTimeout(idleLoop, 1000);
    };
    idleTimer = window.setTimeout(idleLoop, 1000);

    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('popstate', onPopState);
      window.removeEventListener('scroll', onScroll as any);
      if (idleTimer) window.clearTimeout(idleTimer);
      if (dwellTimer) window.clearInterval(dwellTimer);
    };
  }, []);

  useEffect(() => {
    let timer: number | undefined;

    const batchSend = async () => {
      if (!sessionId || !userId) return;
      // Embed a replay nonce per batch (mitigates naive replay)
      const nonce = Math.random().toString(36).slice(2);
      const telemetry: Telemetry = bufferRef.current.reduce((acc, cur) => ({ ...acc, ...cur }), { replay_nonce: nonce });
      bufferRef.current = [];
      if (Object.keys(telemetry).length === 0) return;
      try {
        await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId,
            ...(getCsrfToken() ? { 'X-CSRF-Token': getCsrfToken() as string } : {}),
          },
          credentials: 'include',
          body: JSON.stringify({ session_id: sessionId, user_id: userId, telemetry }),
        });
        if (onRiskChange) {
          const res = await fetch(`${statusEndpoint}/${encodeURIComponent(sessionId)}`, { credentials: 'include' });
          if (res.ok) {
            const data = await res.json();
            const level = (data.risk_level || 'low') as 'low' | 'medium' | 'high';
            const score = Number(data.risk_score || 0);
            onRiskChange(level, score);
          }
        }
      } catch (e) {
        // swallow
      }
    };

    timer = window.setInterval(batchSend, intervalMs);
    return () => {
      if (timer) window.clearInterval(timer);
    };
  }, [sessionId, userId, intervalMs, endpoint, statusEndpoint, onRiskChange]);
}
