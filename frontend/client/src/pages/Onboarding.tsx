import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { useLocation } from "wouter";
import { motion } from "framer-motion";
import { Keyboard, Smartphone, MapPin, CheckCircle, MousePointer, Move, Hand, Navigation } from "lucide-react";
import { useDeviceInfo } from "@/hooks/use-device-info";
import { useTypingAnalysis } from "@/hooks/use-typing-analysis";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const TYPING_SAMPLE = "The quick brown fox jumps over the lazy dog and runs through the forest.";

// Behavioral activity interface
interface BehavioralData {
  typingAnalysis: {
    wpm: number;
    accuracy: number;
    keystrokeTimings: number[];
  };
  mouseMovement: {
    totalDistance: number;
    avgSpeed: number;
    clicks: number;
    trajectory: Array<{x: number, y: number, timestamp: number}>;
  };
  touchInteraction: {
    touchPoints: number;
    pressure: number[];
    gestures: string[];
  };
  scrollBehavior: {
    totalScroll: number;
    scrollSpeed: number;
    scrollPattern: number[];
  };
  dragDrop: {
    attempts: number;
    accuracy: number;
    completionTime: number;
  };
  locationData: {
    latitude: number;
    longitude: number;
    accuracy: number;
    timestamp: number;
  } | null;
}

// Add helper for base64url encoding
function bufferToBase64url(buffer: ArrayBuffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

export default function Onboarding() {
  const [, setLocation] = useLocation();
  const [currentActivity, setCurrentActivity] = useState(0);
  const [activityProgress, setActivityProgress] = useState(0);
  const [locationRequired, setLocationRequired] = useState(false);
  const [behavioralData, setBehavioralData] = useState<Partial<BehavioralData>>({});
  
  // Activity completion states
  const [typingComplete, setTypingComplete] = useState(false);
  const [mouseComplete, setMouseComplete] = useState(false);
  const [touchComplete, setTouchComplete] = useState(false);
  const [scrollComplete, setScrollComplete] = useState(false);
  const [dragDropComplete, setDragDropComplete] = useState(false);
  const [locationComplete, setLocationComplete] = useState(false);
  // New: Only one of mouse or touch is required
  const mouseOrTouchComplete = mouseComplete || touchComplete;
  
  // Refs for tracking
  const mouseTrackingRef = useRef<HTMLDivElement>(null);
  const scrollTrackingRef = useRef<HTMLDivElement>(null);
  const dragDropRef = useRef<HTMLDivElement>(null);
  const touchZoneRef = useRef<HTMLDivElement>(null);
  
  const deviceInfo = useDeviceInfo();
  const { toast } = useToast();
  
  const {
    text,
    setText,
    wpm,
    accuracy,
    typingProgress,
    isComplete: typingAnalysisComplete
  } = useTypingAnalysis(TYPING_SAMPLE);

  // Calculate total progress based on completed activities
  useEffect(() => {
    // Only one of mouse or touch is required
    const activities = [typingComplete, mouseOrTouchComplete, scrollComplete, dragDropComplete, locationComplete];
    const completedCount = activities.filter(Boolean).length;
    const progress = Math.round((completedCount / 5) * 100);
    setActivityProgress(progress);
  }, [typingComplete, mouseOrTouchComplete, scrollComplete, dragDropComplete, locationComplete]);

  // Update typing completion
  useEffect(() => {
    if (typingAnalysisComplete && !typingComplete) {
      setTypingComplete(true);
      setBehavioralData(prev => ({
        ...prev,
        typingAnalysis: {
          wpm,
          accuracy,
          keystrokeTimings: [] // Would be populated with real keystroke timing data
        }
      }));
    }
  }, [typingAnalysisComplete, wpm, accuracy]);

  // Mouse movement tracking
  const trackMouseMovement = (e: React.MouseEvent) => {
    if (!mouseTrackingRef.current) return;
    
    const rect = mouseTrackingRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setBehavioralData(prev => {
      const mouseData = prev.mouseMovement || {
        totalDistance: 0,
        avgSpeed: 0,
        clicks: 0,
        trajectory: []
      };
      
      const newTrajectory = [...mouseData.trajectory, { x, y, timestamp: Date.now() }];
      if (newTrajectory.length > 100) { // Keep last 100 points
        newTrajectory.shift();
      }
      
      return {
        ...prev,
        mouseMovement: {
          ...mouseData,
          trajectory: newTrajectory
        }
      };
    });
  };

  const handleMouseClick = () => {
    setBehavioralData(prev => ({
      ...prev,
      mouseMovement: {
        ...prev.mouseMovement!,
        clicks: (prev.mouseMovement?.clicks || 0) + 1
      }
    }));
    // New: If mouse is completed, mark touch as not required
    if ((behavioralData.mouseMovement?.clicks || 0) >= 10 && !mouseComplete && !touchComplete) {
      setMouseComplete(true);
      setTouchComplete(false); // If mouse is done, touch is not needed
      toast({
        title: "Mouse Activity Complete",
        description: "Mouse movement pattern recorded successfully. Touch not required."
      });
    }
  };

  // Touch interaction tracking
  const handleTouchStart = (e: React.TouchEvent) => {
    const touches = e.touches;
    const pressure = 'force' in touches[0] ? (touches[0] as any).force : 0.5;
    
    setBehavioralData(prev => ({
      ...prev,
      touchInteraction: {
        touchPoints: touches.length,
        pressure: [...(prev.touchInteraction?.pressure || []), pressure],
        gestures: [...(prev.touchInteraction?.gestures || []), 'touch']
      }
    }));
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    setBehavioralData(prev => ({
      ...prev,
      touchInteraction: {
        ...prev.touchInteraction!,
        gestures: [...(prev.touchInteraction?.gestures || []), 'swipe']
      }
    }));
    // New: If touch is completed, mark mouse as not required
    if ((behavioralData.touchInteraction?.gestures?.length || 0) >= 20 && !touchComplete && !mouseComplete) {
      setTouchComplete(true);
      setMouseComplete(false); // If touch is done, mouse is not needed
      toast({
        title: "Touch Activity Complete",
        description: "Touch interaction patterns recorded. Mouse not required."
      });
    }
  };

  // Scroll behavior tracking
  const handleScroll = (e: React.UIEvent) => {
    const scrollTop = e.currentTarget.scrollTop;
    
    setBehavioralData(prev => ({
      ...prev,
      scrollBehavior: {
        totalScroll: scrollTop,
        scrollSpeed: Math.abs(scrollTop - (prev.scrollBehavior?.totalScroll || 0)),
        scrollPattern: [...(prev.scrollBehavior?.scrollPattern || []), scrollTop]
      }
    }));
    
    if (scrollTop > 300 && !scrollComplete) {
      setScrollComplete(true);
      toast({
        title: "Scroll Activity Complete",
        description: "Scroll behavior pattern recorded."
      });
    }
  };

  // Drag and drop functionality
  const [draggedItem, setDraggedItem] = useState<string | null>(null);
  const [dropTargets, setDropTargets] = useState({
    target1: '',
    target2: '',
    target3: ''
  });
  const [dragStartTime, setDragStartTime] = useState(0);

  const handleDragStart = (e: React.DragEvent, item: string) => {
    setDraggedItem(item);
    setDragStartTime(Date.now());
  };

  const handleDrop = (e: React.DragEvent, target: string) => {
    e.preventDefault();
    if (!draggedItem) return;
    
    const completionTime = Date.now() - dragStartTime;
    
    setDropTargets(prev => ({
      ...prev,
      [target]: draggedItem
    }));
    
    setBehavioralData(prev => ({
      ...prev,
      dragDrop: {
        attempts: (prev.dragDrop?.attempts || 0) + 1,
        accuracy: target === `target${draggedItem.slice(-1)}` ? 100 : 0,
        completionTime
      }
    }));
    
    setDraggedItem(null);
    
    // Check if all items are correctly placed
    const newTargets = { ...dropTargets, [target]: draggedItem };
    const correctPlacements = Object.entries(newTargets).filter(([key, value]) => 
      key === `target${value.slice(-1)}`
    ).length;
    
    if (correctPlacements === 3 && !dragDropComplete) {
      setDragDropComplete(true);
      toast({
        title: "Drag & Drop Complete",
        description: "Drag and drop activity completed successfully."
      });
    }
  };

  // Mandatory location access
  const requestLocationAccess = () => {
    if (!navigator.geolocation) {
      toast({
        title: "Location Not Supported",
        description: "Your device doesn't support location services.",
        variant: "destructive"
      });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const locationData = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: Date.now()
        };
        
        setBehavioralData(prev => ({
          ...prev,
          locationData
        }));
        
        setLocationComplete(true);
        toast({
          title: "Location Access Granted",
          description: "Location data captured for security profiling."
        });
      },
      (error) => {
        toast({
          title: "Location Access Required",
          description: "Location access is mandatory for account security. Please enable location services.",
          variant: "destructive"
        });
        setLocationRequired(true);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000
      }
    );
  };

  // Force location access on component mount
  useEffect(() => {
    requestLocationAccess();
  }, []);

  const completeMutation = useMutation({
    mutationFn: async () => {
      const email = localStorage.getItem("securebank_pending_email");
      if (!email) throw new Error("No pending registration found");
      
      const response = await apiRequest("POST", "/api/auth/complete-onboarding", {
        email,
        deviceFingerprint: deviceInfo,
        behaviorProfile: {
          ...behavioralData,
          deviceInfo,
          completedActivities: {
            typing: typingComplete,
            mouse: mouseComplete,
            touch: touchComplete,
            scroll: scrollComplete,
            dragDrop: dragDropComplete,
            location: locationComplete
          }
        },
      });
      return await response.json();
    },
    onSuccess: (data) => {
      localStorage.removeItem("securebank_pending_email");
      localStorage.setItem("securebank_user", JSON.stringify(data.user));
      toast({
        title: "Behavioral Profile Complete!",
        description: "Your comprehensive security profile has been created.",
      });
      setLocation("/dashboard");
    },
    onError: (error: any) => {
      toast({
        title: "Profile Creation Failed",
        description: error.message || "Please complete all activities first.",
        variant: "destructive",
      });
    },
  });

  const handleComplete = () => {
    if (activityProgress < 100) {
      toast({
        title: "Complete All Activities",
        description: "Please finish all behavioral activities before proceeding.",
        variant: "destructive",
      });
      return;
    }
    completeMutation.mutate();
  };

  // Add state for WebAuthn registration
  const [showWebAuthnModal, setShowWebAuthnModal] = useState(false);
  const [webauthnInProgress, setWebauthnInProgress] = useState(false);
  const [webauthnError, setWebauthnError] = useState<string | null>(null);
  const [webauthnSuccess, setWebauthnSuccess] = useState(false);

  // Activities for status display
  const activities = [
    { name: "Typing Analysis", completed: typingComplete, icon: Keyboard },
    { name: "Mouse or Touch", completed: mouseOrTouchComplete, icon: mouseComplete ? MousePointer : Hand },
    { name: "Scroll Behavior", completed: scrollComplete, icon: Move },
    { name: "Drag & Drop", completed: dragDropComplete, icon: Move },
    { name: "Location Services", completed: locationComplete, icon: Navigation }
  ];

  return (
    <section className="py-8 min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center mb-6">
              <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center mr-2">
                <span className="text-gray-500 text-xs">1</span>
              </div>
              <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center mr-2">
                <span className="text-gray-500 text-xs">2</span>
              </div>
              <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                <span className="text-white text-xs">3</span>
              </div>
            </div>
            
            <h1 className="text-4xl font-bold text-gray-900 mb-4">Advanced Behavioral Profiling</h1>
            <p className="text-lg text-gray-600 mb-4">Complete all activities to create your comprehensive security profile</p>
            
            {/* Activity Status */}
            <div className="flex flex-wrap justify-center gap-2 mb-6">
              {activities.map((activity, index) => (
                <div key={index} className={`flex items-center px-3 py-1 rounded-full text-sm ${
                  activity.completed ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                }`}>
                  <activity.icon className="h-4 w-4 mr-1" />
                  {activity.name}
                  {activity.completed && <CheckCircle className="h-4 w-4 ml-1" />}
                </div>
              ))}
            </div>
            
            <Progress value={activityProgress} className="max-w-md mx-auto h-3 mb-2" />
            <p className="text-sm text-gray-600">{activityProgress}% Complete</p>
          </div>

          {/* Activity Grid */}
          <div className="grid lg:grid-cols-3 md:grid-cols-2 gap-6 mb-8">
            
            {/* 1. Typing Analysis */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <Card className={`h-full ${typingComplete ? 'ring-2 ring-green-500' : ''}`}>
                <CardHeader>
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                      <Keyboard className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Typing Analysis</CardTitle>
                      <p className="text-sm text-gray-600">Pattern recognition</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="mb-4">
                    <p className="text-gray-700 mb-3 p-3 bg-gray-50 rounded text-sm">
                      "{TYPING_SAMPLE}"
                    </p>
                    <Textarea
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      className="w-full h-20 resize-none text-sm"
                      placeholder="Type the sentence above..."
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span>Speed: {wpm} WPM</span>
                      <span>Accuracy: {accuracy}%</span>
                    </div>
                    <Progress value={typingProgress} className="h-2" />
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* 2. Mouse Movement Tracking */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Card className={`h-full ${mouseComplete ? 'ring-2 ring-green-500' : ''}`}>
                <CardHeader>
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mr-3">
                      <MousePointer className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Mouse Movement</CardTitle>
                      <p className="text-sm text-gray-600">Track cursor patterns</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div
                    ref={mouseTrackingRef}
                    onMouseMove={trackMouseMovement}
                    onClick={handleMouseClick}
                    className="w-full h-32 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center cursor-crosshair bg-gradient-to-br from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 transition-colors"
                  >
                    <div className="text-center">
                      <MousePointer className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                      <p className="text-sm text-gray-600">Move mouse and click here</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Clicks: {behavioralData.mouseMovement?.clicks || 0}/10
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* 3. Touch Interaction */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <Card className={`h-full ${touchComplete ? 'ring-2 ring-green-500' : ''}`}>
                <CardHeader>
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center mr-3">
                      <Hand className="h-5 w-5 text-orange-600" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Touch & Pressure</CardTitle>
                      <p className="text-sm text-gray-600">Multi-touch gestures</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div
                    ref={touchZoneRef}
                    onTouchStart={handleTouchStart}
                    onTouchMove={handleTouchMove}
                    className="w-full h-32 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center bg-gradient-to-br from-orange-50 to-yellow-50 touch-manipulation"
                  >
                    <div className="text-center">
                      <Hand className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                      <p className="text-sm text-gray-600">Touch and swipe here</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Gestures: {behavioralData.touchInteraction?.gestures?.length || 0}/20
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* 4. Scroll Behavior */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <Card className={`h-full ${scrollComplete ? 'ring-2 ring-green-500' : ''}`}>
                <CardHeader>
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mr-3">
                      <Move className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Scroll Patterns</CardTitle>
                      <p className="text-sm text-gray-600">Scroll behavior analysis</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div
                    ref={scrollTrackingRef}
                    onScroll={handleScroll}
                    className="w-full h-32 border-2 border-dashed border-gray-300 rounded-lg overflow-y-auto bg-gradient-to-b from-green-50 to-teal-50"
                  >
                    <div className="p-4 space-y-4">
                      <p className="text-sm">Scroll down to analyze your scrolling pattern...</p>
                      <div className="h-20 bg-green-100 rounded p-2">
                        <p className="text-xs">Scroll content area 1</p>
                      </div>
                      <div className="h-20 bg-green-200 rounded p-2">
                        <p className="text-xs">Scroll content area 2</p>
                      </div>
                      <div className="h-20 bg-green-300 rounded p-2">
                        <p className="text-xs">Scroll content area 3</p>
                      </div>
                      <div className="h-20 bg-green-400 rounded p-2">
                        <p className="text-xs">Scroll content area 4 - Keep scrolling!</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* 5. Drag & Drop Activity */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.5 }}
            >
              <Card className={`h-full ${dragDropComplete ? 'ring-2 ring-green-500' : ''}`}>
                <CardHeader>
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center mr-3">
                      <Move className="h-5 w-5 text-indigo-600" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Drag & Drop</CardTitle>
                      <p className="text-sm text-gray-600">Precision tracking</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Draggable Items */}
                    <div className="flex gap-2 mb-3">
                      {['item1', 'item2', 'item3'].map((item) => (
                        <div
                          key={item}
                          draggable
                          onDragStart={(e) => handleDragStart(e, item)}
                          className="px-3 py-2 bg-indigo-100 text-indigo-800 rounded-lg cursor-move text-sm hover:bg-indigo-200 transition-colors"
                        >
                          {item.replace('item', 'Item ')}
                        </div>
                      ))}
                    </div>
                    
                    {/* Drop Targets */}
                    <div className="grid grid-cols-3 gap-2">
                      {['target1', 'target2', 'target3'].map((target) => (
                        <div
                          key={target}
                          onDragOver={(e) => e.preventDefault()}
                          onDrop={(e) => handleDrop(e, target)}
                          className={`h-16 border-2 border-dashed rounded-lg flex items-center justify-center text-xs transition-colors ${
                            dropTargets[target as keyof typeof dropTargets]
                              ? 'border-green-500 bg-green-50'
                              : 'border-gray-300 bg-gray-50'
                          }`}
                        >
                          {dropTargets[target as keyof typeof dropTargets] || `Drop Zone ${target.slice(-1)}`}
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* 6. Location Services (Mandatory) */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            >
              <Card className={`h-full ${locationComplete ? 'ring-2 ring-green-500' : 'ring-2 ring-red-500'}`}>
                <CardHeader>
                  <div className="flex items-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center mr-3 ${
                      locationComplete ? 'bg-green-100' : 'bg-red-100'
                    }`}>
                      <Navigation className={`h-5 w-5 ${
                        locationComplete ? 'text-green-600' : 'text-red-600'
                      }`} />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Location Access</CardTitle>
                      <p className="text-sm text-red-600 font-medium">Required for Security</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-center space-y-4">
                    {locationComplete ? (
                      <div className="text-green-600">
                        <CheckCircle className="h-12 w-12 mx-auto mb-2" />
                        <p className="font-medium">Location Captured</p>
                        <p className="text-xs text-gray-600">Security profile enhanced</p>
                      </div>
                    ) : (
                      <>
                        <Navigation className="h-12 w-12 mx-auto text-red-500 mb-2" />
                        <p className="text-sm text-gray-700 mb-3">
                          Location access is mandatory for fraud prevention and account security.
                        </p>
                        <Button
                          onClick={requestLocationAccess}
                          className="w-full bg-red-600 hover:bg-red-700 text-white"
                        >
                          Grant Location Access
                        </Button>
                        {locationRequired && (
                          <p className="text-xs text-red-600 mt-2">
                            Please enable location services to continue
                          </p>
                        )}
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Completion Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.7 }}
            className="text-center"
          >
            <Card className="max-w-2xl mx-auto">
              <CardContent className="pt-6">
                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-2">Behavioral Profile Status</h3>
                  <Progress value={activityProgress} className="w-full h-4 mb-2" />
                  <p className="text-sm text-gray-600">{activityProgress}% of activities completed</p>
                </div>
                
                <Button
                  onClick={handleComplete}
                  className="w-full max-w-md mx-auto h-12 text-lg font-medium"
                  disabled={activityProgress < 100 || completeMutation.isPending}
                >
                  {completeMutation.isPending 
                    ? "Creating Your Security Profile..." 
                    : activityProgress < 100
                    ? `Complete ${6 - activities.filter(a => a.completed).length} More Activities`
                    : "Create Security Profile & Continue"
                  }
                </Button>
                
                <p className="text-sm text-gray-500 mt-4">
                  {activityProgress < 100 
                    ? "All behavioral activities must be completed for maximum security." 
                    : "Your comprehensive behavioral profile is ready for creation!"
                  }
                </p>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>
      {activityProgress === 100 && !webauthnSuccess && (
        <Button
          variant="outline"
          className="w-full max-w-md mx-auto h-12 text-lg font-medium mt-4"
          onClick={() => setShowWebAuthnModal(true)}
          disabled={webauthnInProgress}
        >
          Register Biometric Device (Recommended)
        </Button>
      )}
      <Dialog open={showWebAuthnModal} onOpenChange={setShowWebAuthnModal}>
        <DialogContent>
          <DialogTitle>Register Biometric Device</DialogTitle>
          <DialogDescription>
            {webauthnSuccess ? (
              <div className="text-green-600 font-medium">Biometric device registered successfully! You can now use biometrics to log in.</div>
            ) : (
              <>
                <div className="mb-2">For maximum security, register your device for biometric login (Face ID, Touch ID, Windows Hello, or security key).</div>
                {webauthnError && <div className="text-red-600 text-xs mb-2">{webauthnError}</div>}
                <Button
                  disabled={webauthnInProgress}
                  onClick={async () => {
                    setWebauthnInProgress(true);
                    setWebauthnError(null);
                    try {
                      const email = localStorage.getItem("securebank_pending_email");
                      if (!email) throw new Error("No pending registration found");
                      // 1. Begin registration
                      const begin = await apiRequest("POST", "/api/auth/webauthn/register/begin", { identifier: email });
                      const { publicKey, challenge_id } = await begin.json ? await begin.json() : begin;
                      // 2. Prepare publicKey for navigator.credentials.create
                      publicKey.challenge = Uint8Array.from(atob(publicKey.challenge), c => c.charCodeAt(0));
                      publicKey.user.id = Uint8Array.from(atob(publicKey.user.id), c => c.charCodeAt(0));
                      // 3. navigator.credentials.create
                      const credential = await navigator.credentials.create({ publicKey });
                      if (!credential) throw new Error("Biometric registration failed or was cancelled.");
                      // 4. Prepare credential for backend
                      const cred = credential as PublicKeyCredential;
                      const credentialData = {
                        id: cred.id,
                        type: cred.type,
                        rawId: bufferToBase64url(cred.rawId),
                        response: {
                          attestationObject: bufferToBase64url((cred.response as any).attestationObject),
                          clientDataJSON: bufferToBase64url((cred.response as any).clientDataJSON),
                        },
                        authenticatorAttachment: (cred as any).authenticatorAttachment,
                        transports: (cred as any).getTransports ? (cred as any).getTransports() : undefined,
                      };
                      // 5. Complete registration
                      const complete = await apiRequest("POST", "/api/auth/webauthn/register/complete", { identifier: email, credential: credentialData, challenge_id });
                      const result = await complete.json ? await complete.json() : complete;
                      if (result.success) {
                        setWebauthnSuccess(true);
                        toast({ title: "Biometric Registered", description: "You can now use biometrics to log in." });
                      } else {
                        throw new Error(result.message || "WebAuthn registration failed.");
                      }
                    } catch (e: any) {
                      setWebauthnError(e.message || "WebAuthn registration failed");
                    }
                    setWebauthnInProgress(false);
                  }}
                >
                  {webauthnInProgress ? "Registering..." : "Register Now"}
                </Button>
                <Button
                  variant="ghost"
                  className="mt-2"
                  onClick={() => setShowWebAuthnModal(false)}
                  disabled={webauthnInProgress}
                >
                  Skip for now
                </Button>
              </>
            )}
          </DialogDescription>
        </DialogContent>
      </Dialog>
    </section>
  );
}
