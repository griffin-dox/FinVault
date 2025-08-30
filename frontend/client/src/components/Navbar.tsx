import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";
import { Link, useLocation } from "wouter";
import { Shield, User, LogOut, Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { HealthIndicator } from "./HealthIndicator";

export default function Navbar() {
  const { user, logout } = useAuth();
  const [location] = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const onLanding = location === "/";

  const isActive = (path: string) => location === path;

  const navigationLinks = user ? [
    { href: "/dashboard", label: "Dashboard", active: isActive("/dashboard") },
    { href: "/transactions", label: "Transactions", active: isActive("/transactions") },
    ...(user.isAdmin ? [{ href: "/admin", label: "Admin", active: isActive("/admin"), isAdmin: true }] : []),
  ] : [];

  const handleLogout = () => {
    logout();
    setIsMobileMenuOpen(false);
  };

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 fixed w-full top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/">
            <div className="flex items-center space-x-2 cursor-pointer">
              <Shield className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold text-gray-900">SecureBank</span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            {navigationLinks.map((link) => (
              <Link key={link.href} href={link.href}>
                <button
                  className={`text-sm font-medium transition-colors ${
                    link.active
                      ? link.isAdmin 
                        ? "text-red-600 border-b-2 border-red-600 pb-1" 
                        : "text-primary border-b-2 border-primary pb-1"
                      : link.isAdmin
                        ? "text-red-600 hover:text-red-700"
                        : "text-gray-700 hover:text-primary"
                  }`}
                >
                  {link.label}
                </button>
              </Link>
            ))}
  
            {/* Health Indicator */}
            <HealthIndicator showDetailsOnClick={true} />
          </div>

          {/* Desktop User Menu / Auth Buttons */}
          <div className="hidden md:flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-4">
                {/* User Info */}
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-700">{user.name}</p>
                      <div className="flex items-center space-x-1">
                        {user.isAdmin && (
                          <Badge variant="secondary" className="text-xs bg-red-100 text-red-700 border-red-200 mr-1">
                            Admin
                          </Badge>
                        )}
                        <div className={`w-2 h-2 rounded-full ${
                          user.riskLevel === "low" ? "bg-green-400" :
                          user.riskLevel === "medium" ? "bg-yellow-400" : "bg-red-400"
                        }`}></div>
                        <span className="text-xs text-gray-500 capitalize">{user.riskLevel} Risk</span>
                      </div>
                    </div>
                  </div>
                  <div className="h-6 w-px bg-gray-300"></div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleLogout}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <LogOut className="h-4 w-4 mr-1" />
                    Logout
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                {!onLanding && (
                  <>
                    <Link href="/login">
                      <Button variant="ghost" size="sm">
                        Login
                      </Button>
                    </Link>
                    <Link href="/register">
                      <Button size="sm" className="banking-button-primary">
                        Register
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-white border-t border-gray-200"
          >
            <div className="px-4 py-4 space-y-4">
              {/* Mobile Navigation Links */}
              {navigationLinks.map((link) => (
                <Link key={link.href} href={link.href}>
                  <button
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`block w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      link.active
                        ? link.isAdmin
                          ? "bg-red-100 text-red-700"
                          : "bg-primary/10 text-primary"
                        : link.isAdmin
                          ? "text-red-600 hover:bg-red-50"
                          : "text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    {link.label}
                  </button>
                </Link>
              ))}

              {/* Mobile Health Check Link */}
              <Link href="/health">
                <button
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`block w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive("/health")
                      ? "bg-primary/10 text-primary"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  System Health
                </button>
              </Link>

              {/* Mobile User Info / Auth */}
              <div className="pt-4 border-t border-gray-200">
                {user ? (
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3 px-3 py-2">
                      <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                        <User className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{user.name}</p>
                        <div className="flex items-center space-x-1">
                          {user.isAdmin && (
                            <Badge variant="secondary" className="text-xs bg-red-100 text-red-700 border-red-200 mr-1">
                              Admin
                            </Badge>
                          )}
                          <div className={`w-2 h-2 rounded-full ${
                            user.riskLevel === "low" ? "bg-green-400" :
                            user.riskLevel === "medium" ? "bg-yellow-400" : "bg-red-400"
                          }`}></div>
                          <span className="text-xs text-gray-500 capitalize">{user.riskLevel} Risk</span>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleLogout}
                      className="w-full justify-start text-gray-500 hover:text-gray-700"
                    >
                      <LogOut className="h-4 w-4 mr-2" />
                      Logout
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {!onLanding && (
                      <>
                        <Link href="/login">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="w-full justify-start"
                            onClick={() => setIsMobileMenuOpen(false)}
                          >
                            Login
                          </Button>
                        </Link>
                        <Link href="/register">
                          <Button
                            size="sm"
                            className="w-full banking-button-primary"
                            onClick={() => setIsMobileMenuOpen(false)}
                          >
                            Register
                          </Button>
                        </Link>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
