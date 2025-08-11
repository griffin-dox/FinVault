#!/usr/bin/env python3
"""
FinVault Code Cleanup Script

This script performs automated cleanup of the codebase:
- Removes debug statements and console logs
- Updates security configurations
- Cleans up unused files
- Validates security policies
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

class CodeCleanup:
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.frontend_dir = self.root_dir / "frontend" / "client"
        self.backend_dir = self.root_dir / "backend"
        
    def cleanup_console_logs(self) -> None:
        """Remove console.log statements from frontend code"""
        print("🧹 Cleaning up console logs...")
        
        # Patterns to remove
        patterns = [
            r'console\.log\([^)]*\);?\s*',
            r'console\.error\([^)]*\);?\s*',
            r'console\.warn\([^)]*\);?\s*',
            r'console\.debug\([^)]*\);?\s*',
            r'console\.info\([^)]*\);?\s*',
        ]
        
        # Keep essential error logging
        keep_patterns = [
            r'console\.error.*ErrorBoundary.*',
            r'console\.error.*Failed to parse.*',
        ]
        
        for file_path in self.frontend_dir.rglob("*.ts*"):
            if file_path.is_file() and "node_modules" not in str(file_path):
                self._clean_file_logs(file_path, patterns, keep_patterns)
    
    def _clean_file_logs(self, file_path: Path, patterns: List[str], keep_patterns: List[str]) -> None:
        """Clean console logs from a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Remove console logs
            for pattern in patterns:
                content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
            # Restore essential logs
            for pattern in keep_patterns:
                matches = re.findall(pattern, original_content, re.MULTILINE)
                for match in matches:
                    if match not in content:
                        # Find appropriate place to reinsert
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'export' in line or 'import' in line:
                                lines.insert(i, match)
                                break
                        content = '\n'.join(lines)
            
            # Clean up multiple empty lines
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ Cleaned {file_path.relative_to(self.root_dir)}")
                
        except Exception as e:
            print(f"  ❌ Error cleaning {file_path}: {e}")
    
    def cleanup_python_prints(self) -> None:
        """Remove print statements from Python code"""
        print("🐍 Cleaning up Python print statements...")
        
        patterns = [
            r'print\([^)]*\);?\s*',
            r'logging\.debug\([^)]*\);?\s*',
            r'logging\.info\([^)]*\);?\s*',
        ]
        
        # Keep essential logging
        keep_patterns = [
            r'print.*WARNING.*',
            r'print.*ERROR.*',
            r'logging\.error.*',
            r'logging\.warning.*',
        ]
        
        for file_path in self.backend_dir.rglob("*.py"):
            if file_path.is_file() and "__pycache__" not in str(file_path):
                self._clean_file_logs(file_path, patterns, keep_patterns)
    
    def remove_build_artifacts(self) -> None:
        """Remove build artifacts and temporary files"""
        print("🗑️  Removing build artifacts...")
        
        # Directories to remove
        dirs_to_remove = [
            self.frontend_dir / "dist",
            self.frontend_dir / "node_modules",
            self.backend_dir / "__pycache__",
            self.root_dir / "venv",
        ]
        
        for dir_path in dirs_to_remove:
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    print(f"  ✅ Removed {dir_path.relative_to(self.root_dir)}")
                except Exception as e:
                    print(f"  ❌ Error removing {dir_path}: {e}")
        
        # Files to remove
        files_to_remove = [
            self.frontend_dir / "package-lock.json",
            self.frontend_dir / "yarn.lock",
        ]
        
        for file_path in files_to_remove:
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"  ✅ Removed {file_path.relative_to(self.root_dir)}")
                except Exception as e:
                    print(f"  ❌ Error removing {file_path}: {e}")
    
    def update_security_headers(self) -> None:
        """Update security headers in static.json"""
        print("🔒 Updating security headers...")
        
        static_json_path = self.frontend_dir / "static.json"
        if static_json_path.exists():
            try:
                with open(static_json_path, 'r') as f:
                    content = f.read()
                
                # Update security headers
                security_headers = {
                    "Cache-Control": "public, max-age=0, must-revalidate",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "X-XSS-Protection": "1; mode=block",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://finvault-g6r7.onrender.com;"
                }
                
                # Update the headers section
                headers_section = '"headers": {\n    "/**": {\n'
                for key, value in security_headers.items():
                    headers_section += f'      "{key}": "{value}",\n'
                headers_section = headers_section.rstrip(',\n') + '\n    },\n'
                
                # Replace existing headers
                content = re.sub(
                    r'"headers":\s*{[^}]+}',
                    headers_section.rstrip(',\n') + '  }',
                    content,
                    flags=re.DOTALL
                )
                
                with open(static_json_path, 'w') as f:
                    f.write(content)
                
                print(f"  ✅ Updated security headers in {static_json_path.relative_to(self.root_dir)}")
                
            except Exception as e:
                print(f"  ❌ Error updating security headers: {e}")
    
    def create_env_example(self) -> None:
        """Create .env.example files"""
        print("📝 Creating environment example files...")
        
        # Frontend .env.example
        frontend_env_example = """# Frontend Environment Variables
# Copy this file to .env and update with your values

# API Configuration
VITE_API_URL=https://finvault-g6r7.onrender.com

# Development API URL (uncomment for local development)
# VITE_API_URL=http://localhost:8000

# Feature Flags
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_DEBUG=false

# Security
VITE_ENABLE_HTTPS=true
"""
        
        with open(self.frontend_dir / ".env.example", 'w') as f:
            f.write(frontend_env_example)
        
        # Backend .env.example
        backend_env_example = """# Backend Environment Variables
# Copy this file to .env and update with your values

# Database Configuration
POSTGRES_URI=postgresql://username:password@localhost:5432/finvault
MONGODB_URI=mongodb://localhost:27017/finvault
REDIS_URI=redis://localhost:6379

# Security
JWT_SECRET=your-super-secret-jwt-key-here
ENVIRONMENT=development

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# SMS Configuration (for production)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
"""
        
        with open(self.backend_dir / ".env.example", 'w') as f:
            f.write(backend_env_example)
        
        print("  ✅ Created .env.example files")
    
    def validate_security(self) -> List[str]:
        """Validate security configurations"""
        print("🔍 Validating security configurations...")
        
        issues = []
        
        # Check for hardcoded secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]
        
        for pattern in secret_patterns:
            for file_path in self.root_dir.rglob("*.py"):
                if file_path.is_file() and "__pycache__" not in str(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            issues.append(f"Potential hardcoded secret in {file_path}: {matches}")
        
        # Check for exposed environment variables
        for file_path in self.frontend_dir.rglob("*.ts*"):
            if file_path.is_file() and "node_modules" not in str(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "process.env" in content and "VITE_" not in content:
                        issues.append(f"Non-VITE environment variable in {file_path}")
        
        if issues:
            print("  ⚠️  Security issues found:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("  ✅ No security issues found")
        
        return issues
    
    def run_cleanup(self) -> None:
        """Run the complete cleanup process"""
        print("🚀 Starting FinVault Code Cleanup...")
        print("=" * 50)
        
        # Run cleanup tasks
        self.cleanup_console_logs()
        self.cleanup_python_prints()
        self.remove_build_artifacts()
        self.update_security_headers()
        self.create_env_example()
        
        # Validate security
        issues = self.validate_security()
        
        print("=" * 50)
        print("✅ Cleanup completed!")
        
        if issues:
            print(f"⚠️  Found {len(issues)} security issues to address")
        else:
            print("🎉 No security issues found!")

def main():
    """Main function"""
    cleanup = CodeCleanup()
    cleanup.run_cleanup()

if __name__ == "__main__":
    main() 