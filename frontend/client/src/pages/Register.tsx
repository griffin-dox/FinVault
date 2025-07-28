import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { registerSchema, type RegisterInput } from "@shared/schema";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { Link } from "wouter";
import { COUNTRIES } from "@/lib/constants";

export default function Register() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  
  const form = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      email: "",
      phone: "",
      country: "",
      agreeToTerms: false,
    },
  });

  const registerMutation = useMutation({
    mutationFn: async (data: RegisterInput) => {
      // Filter out frontend-only fields before sending to backend
      const { country, agreeToTerms, ...backendData } = data;
      const response = await apiRequest("POST", "/api/auth/register", backendData);
      return await response.json();
    },
    onSuccess: (data) => {
      localStorage.setItem("securebank_pending_email", form.getValues("email"));
      toast({
        title: "Registration Successful",
        description: "Please check your email to verify your account.",
      });
      setLocation("/verify-email");
    },
    onError: (error: any) => {
      console.log("Registration error object:", error);
      if (error && error.detail && typeof error.detail === "object" && error.detail.message === "User already exists.") {
        const { verified, onboarding_complete } = error.detail;
        if (!verified) {
          toast({
            title: "Email Verification Required",
            description: "Please verify your email to continue.",
          });
          setLocation("/verify-email");
          return;
        } else if (verified && !onboarding_complete) {
          toast({
            title: "Complete Onboarding",
            description: "Please finish onboarding to continue.",
          });
          setLocation("/onboarding");
          return;
        } else if (verified && onboarding_complete) {
          toast({
            title: "Account Exists",
            description: "Please log in to your account.",
          });
          setLocation("/login");
          return;
        }
      }
      toast({
        title: "Registration Failed",
        description: error?.detail?.message || error?.message || "Something went wrong",
        variant: "destructive",
      });
    },
  });

  const onSubmit = (data: RegisterInput) => {
    registerMutation.mutate(data);
  };

  return (
    <section className="py-12 min-h-screen bg-gray-50">
      <div className="max-w-md mx-auto px-4">
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
                <div className="flex items-center space-x-2">
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <span className="text-white text-xs font-bold">1</span>
                  </div>
                  <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-gray-500 text-xs font-bold">2</span>
                  </div>
                  <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-gray-500 text-xs font-bold">3</span>
                  </div>
                </div>
              </div>
              <CardTitle className="text-2xl font-bold text-gray-900">Create Your Account</CardTitle>
              <p className="text-gray-600">Join the future of secure banking</p>
            </CardHeader>
            
            <CardContent>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <div>
                  <Label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                    Full Name
                  </Label>
                  <Input
                    id="name"
                    {...form.register("name")}
                    placeholder="Enter your full name"
                    className="w-full"
                  />
                  {form.formState.errors.name && (
                    <p className="text-sm text-red-600 mt-1">{form.formState.errors.name.message}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                    Email Address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    {...form.register("email")}
                    placeholder="Enter your email"
                    className="w-full"
                  />
                  {form.formState.errors.email && (
                    <p className="text-sm text-red-600 mt-1">{form.formState.errors.email.message}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                    Phone Number
                  </Label>
                  <Input
                    id="phone"
                    type="tel"
                    {...form.register("phone")}
                    placeholder="Enter your phone number"
                    className="w-full"
                  />
                  {form.formState.errors.phone && (
                    <p className="text-sm text-red-600 mt-1">{form.formState.errors.phone.message}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="country" className="block text-sm font-medium text-gray-700 mb-2">
                    Country
                  </Label>
                  <Select onValueChange={(value) => form.setValue("country", value)}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select your country" />
                    </SelectTrigger>
                    <SelectContent>
                      {COUNTRIES.map((country) => (
                        <SelectItem key={country.code} value={country.code}>
                          {country.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {form.formState.errors.country && (
                    <p className="text-sm text-red-600 mt-1">{form.formState.errors.country.message}</p>
                  )}
                </div>

                <div className="flex items-start space-x-3">
                  <Checkbox
                    id="terms"
                    checked={form.watch("agreeToTerms")}
                    onCheckedChange={(checked) => form.setValue("agreeToTerms", !!checked)}
                  />
                  <Label htmlFor="terms" className="text-sm text-gray-600 leading-relaxed">
                    I agree to the{" "}
                    <a href="#" className="text-primary hover:text-primary/80 underline">
                      Terms of Service
                    </a>{" "}
                    and{" "}
                    <a href="#" className="text-primary hover:text-primary/80 underline">
                      Privacy Policy
                    </a>
                  </Label>
                </div>
                {form.formState.errors.agreeToTerms && (
                  <p className="text-sm text-red-600">{form.formState.errors.agreeToTerms.message}</p>
                )}

                <Button 
                  type="submit" 
                  className="w-full banking-button-primary"
                  disabled={registerMutation.isPending}
                >
                  {registerMutation.isPending ? "Creating Account..." : "Create Account"}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-sm text-gray-600">
                  Already have an account?{" "}
                  <Link href="/login" className="text-primary hover:text-primary/80 font-medium">
                    Sign in
                  </Link>
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </section>
  );
}
