import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { transferSchema, type TransferInput } from "@shared/schema";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { motion, AnimatePresence } from "framer-motion";
import { X, AlertTriangle, CheckCircle, Clock, DollarSign } from "lucide-react";

interface TransferModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function TransferModal({ isOpen, onClose }: TransferModalProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [riskAssessment, setRiskAssessment] = useState<{
    riskScore: number;
    status: string;
    message: string;
  } | null>(null);

  const form = useForm<TransferInput>({
    resolver: zodResolver(transferSchema),
    defaultValues: {
      recipient: "",
      amount: 0,
      description: "",
    },
  });

  const transferMutation = useMutation({
    mutationFn: async (data: TransferInput) => {
      const response = await apiRequest("POST", "/api/transaction/", {
        ...data,
        user_id: user?.id,
      });
      return await response.json();
    },
    onSuccess: (data) => {
      setRiskAssessment({
        riskScore: data.riskScore,
        status: data.transaction.status,
        message: getStatusMessage(data.riskScore, data.transaction.status),
      });
      
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ["/api/transaction"] });
      
      // Show success toast after 3 seconds and close modal
      setTimeout(() => {
        toast({
          title: "Transfer Processed",
          description: getStatusMessage(data.riskScore, data.transaction.status),
        });
        handleClose();
      }, 3000);
    },
    onError: (error: any) => {
      toast({
        title: "Transfer Failed",
        description: error.message || "Something went wrong",
        variant: "destructive",
      });
    },
  });

  const getStatusMessage = (riskScore: number, status: string) => {
    if (status === "blocked") {
      return "High risk transaction detected. Transfer blocked for manual review.";
    } else if (status === "pending") {
      return "Medium risk detected. Additional verification required.";
    } else {
      return "Transfer approved and processed successfully!";
    }
  };

  const getRiskColor = (riskScore: number) => {
    if (riskScore <= 30) return "text-green-600";
    if (riskScore <= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getRiskBgColor = (riskScore: number) => {
    if (riskScore <= 30) return "bg-green-100 border-green-200";
    if (riskScore <= 60) return "bg-yellow-100 border-yellow-200";
    return "bg-red-100 border-red-200";
  };

  const getRiskIcon = (riskScore: number) => {
    if (riskScore <= 30) return CheckCircle;
    if (riskScore <= 60) return Clock;
    return AlertTriangle;
  };

  const handleClose = () => {
    form.reset();
    setRiskAssessment(null);
    onClose();
  };

  const onSubmit = (data: TransferInput) => {
    transferMutation.mutate(data);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className="w-full max-w-md"
        >
          <Card className="banking-card">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-semibold flex items-center">
                  <DollarSign className="mr-2 h-5 w-5 text-primary" />
                  New Transfer
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClose}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>

            <CardContent>
              {riskAssessment ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-4"
                >
                  {/* Risk Assessment Result */}
                  <div className={`p-4 rounded-lg border ${getRiskBgColor(riskAssessment.riskScore)}`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        {(() => {
                          const Icon = getRiskIcon(riskAssessment.riskScore);
                          return <Icon className={`h-5 w-5 ${getRiskColor(riskAssessment.riskScore)}`} />;
                        })()}
                        <span className={`font-medium ${getRiskColor(riskAssessment.riskScore)}`}>
                          {riskAssessment.message}
                        </span>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Risk Score:</span>
                        <span className="font-medium">{riskAssessment.riskScore}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all duration-500 ${
                            riskAssessment.riskScore <= 30 ? "bg-green-500" :
                            riskAssessment.riskScore <= 60 ? "bg-yellow-500" : "bg-red-500"
                          }`}
                          style={{ width: `${riskAssessment.riskScore}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Status:</span>
                        <Badge 
                          variant={
                            riskAssessment.status === "completed" ? "default" :
                            riskAssessment.status === "pending" ? "secondary" : "destructive"
                          }
                        >
                          {riskAssessment.status.charAt(0).toUpperCase() + riskAssessment.status.slice(1)}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="text-center text-sm text-gray-500">
                    This modal will close automatically in a few seconds...
                  </div>
                </motion.div>
              ) : (
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <div>
                    <Label htmlFor="recipient" className="block text-sm font-medium text-gray-700 mb-2">
                      Recipient Email
                    </Label>
                    <Input
                      id="recipient"
                      type="email"
                      {...form.register("recipient")}
                      placeholder="Enter recipient email"
                      className="w-full"
                    />
                    {form.formState.errors.recipient && (
                      <p className="text-sm text-red-600 mt-1">{form.formState.errors.recipient.message}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-2">
                      Amount
                    </Label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                      <Input
                        id="amount"
                        type="number"
                        step="0.01"
                        min="0.01"
                        {...form.register("amount", { valueAsNumber: true })}
                        placeholder="0.00"
                        className="w-full pl-8"
                      />
                    </div>
                    {form.formState.errors.amount && (
                      <p className="text-sm text-red-600 mt-1">{form.formState.errors.amount.message}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                      Note (Optional)
                    </Label>
                    <Textarea
                      id="description"
                      {...form.register("description")}
                      placeholder="Add a note for this transfer"
                      className="w-full resize-none"
                      rows={3}
                    />
                    {form.formState.errors.description && (
                      <p className="text-sm text-red-600 mt-1">{form.formState.errors.description.message}</p>
                    )}
                  </div>

                  <div className="flex space-x-4 pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleClose}
                      className="flex-1 banking-button-secondary"
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      className="flex-1 banking-button-primary"
                      disabled={transferMutation.isPending}
                    >
                      {transferMutation.isPending ? "Processing..." : "Send Transfer"}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
