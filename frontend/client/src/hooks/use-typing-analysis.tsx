import { useState, useEffect, useCallback } from "react";

interface TypingMetrics {
  text: string;
  setText: (text: string) => void;
  wpm: number;
  accuracy: number;
  typingProgress: number;
  keystrokes: number;
  errors: number;
  isComplete: boolean;
  startTime: number | null;
  keystrokeTiming: number[];
  reset: () => void;
}

export function useTypingAnalysis(targetText: string): TypingMetrics {
  const [text, setText] = useState("");
  const [startTime, setStartTime] = useState<number | null>(null);
  const [keystrokes, setKeystrokes] = useState(0);
  const [errors, setErrors] = useState(0);
  const [keystrokeTiming, setKeystrokeTiming] = useState<number[]>([]);
  const [lastKeystrokeTime, setLastKeystrokeTime] = useState<number | null>(null);

  // Calculate WPM (Words Per Minute)
  const wpm = (() => {
    if (!startTime || text.length === 0) return 0;
    
    const timeElapsed = (Date.now() - startTime) / 1000 / 60; // in minutes
    const wordsTyped = text.trim().split(/\s+/).length;
    
    return Math.round(wordsTyped / timeElapsed) || 0;
  })();

  // Calculate accuracy percentage
  const accuracy = (() => {
    if (text.length === 0) return 0;
    
    let correctChars = 0;
    const maxLength = Math.min(text.length, targetText.length);
    
    for (let i = 0; i < maxLength; i++) {
      if (text[i] === targetText[i]) {
        correctChars++;
      }
    }
    
    return Math.round((correctChars / text.length) * 100) || 0;
  })();

  // Calculate progress percentage
  const typingProgress = Math.min((text.length / targetText.length) * 100, 100);

  // Check if typing is complete
  const isComplete = text.length > 0 && text.length >= targetText.length * 0.8; // 80% completion

  // Handle text changes
  const handleSetText = useCallback((newText: string) => {
    const now = Date.now();
    
    // Set start time on first keystroke
    if (!startTime && newText.length > 0) {
      setStartTime(now);
    }
    
    // Track keystroke timing
    if (lastKeystrokeTime) {
      const timeDiff = now - lastKeystrokeTime;
      setKeystrokeTiming(prev => [...prev, timeDiff]);
    }
    setLastKeystrokeTime(now);
    
    // Count keystrokes
    if (newText.length > text.length) {
      setKeystrokes(prev => prev + 1);
    }
    
    // Count errors (characters that don't match the target)
    let errorCount = 0;
    const maxLength = Math.min(newText.length, targetText.length);
    
    for (let i = 0; i < maxLength; i++) {
      if (newText[i] !== targetText[i]) {
        errorCount++;
      }
    }
    setErrors(errorCount);
    
    setText(newText);
  }, [text, targetText, startTime, lastKeystrokeTime]);

  // Reset function
  const reset = useCallback(() => {
    setText("");
    setStartTime(null);
    setKeystrokes(0);
    setErrors(0);
    setKeystrokeTiming([]);
    setLastKeystrokeTime(null);
  }, []);

  return {
    text,
    setText: handleSetText,
    wpm,
    accuracy,
    typingProgress,
    keystrokes,
    errors,
    isComplete,
    startTime,
    keystrokeTiming,
    reset,
  };
}

// Hook to analyze typing patterns for behavioral profiling
export function useTypingBehaviorAnalysis(keystrokeTiming: number[]) {
  const [behaviorProfile, setBehaviorProfile] = useState({
    averageKeystrokeTime: 0,
    keystrokeVariance: 0,
    typingRhythm: "regular" as "regular" | "irregular" | "fast" | "slow",
    uniquePattern: "",
  });

  useEffect(() => {
    if (keystrokeTiming.length < 5) return;

    // Calculate average keystroke time
    const average = keystrokeTiming.reduce((sum, time) => sum + time, 0) / keystrokeTiming.length;

    // Calculate variance
    const variance = keystrokeTiming.reduce((sum, time) => sum + Math.pow(time - average, 2), 0) / keystrokeTiming.length;

    // Determine typing rhythm
    let rhythm: "regular" | "irregular" | "fast" | "slow" = "regular";
    if (variance > 10000) { // High variance
      rhythm = "irregular";
    } else if (average < 100) { // Very fast
      rhythm = "fast";
    } else if (average > 300) { // Slow
      rhythm = "slow";
    }

    // Generate a simple unique pattern (simplified for demo)
    const pattern = btoa(
      JSON.stringify({
        avg: Math.round(average),
        var: Math.round(variance),
        rhythm,
        sample: keystrokeTiming.slice(0, 10), // First 10 keystrokes
      })
    );

    setBehaviorProfile({
      averageKeystrokeTime: Math.round(average),
      keystrokeVariance: Math.round(variance),
      typingRhythm: rhythm,
      uniquePattern: pattern,
    });
  }, [keystrokeTiming]);

  return behaviorProfile;
}
