"""
GitHub integration for cloning, pulling, and pushing presets repository
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import json


class GitHubIntegration:
    """Handles GitHub operations for presets repository"""
    
    def __init__(self):
        self.settings = {}
        self.local_path = None
        
    def configure(self, settings: Dict[str, str]):
        """Configure GitHub integration with settings"""
        self.settings = settings
        self.local_path = Path(settings.get('local_path', ''))
        
    def test_connection(self, settings: Dict[str, str]) -> bool:
        """Test if we can connect to the repository"""
        try:
            repo_url = settings['repo_url']
            token = settings.get('github_token', '')
            
            # Add token to URL if provided
            if token and 'github.com' in repo_url:
                repo_url = repo_url.replace('https://', f'https://{token}@')
            
            # Test with git ls-remote
            cmd = ['git', 'ls-remote', '--heads', repo_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0
        except Exception:
            return False
    
    def clone_or_pull(self) -> Tuple[bool, str]:
        """Clone repository if not exists, otherwise pull latest changes"""
        if not self.settings.get('repo_url'):
            return False, "No repository URL configured"
        
        repo_url = self.settings['repo_url']
        token = self.settings.get('github_token', '')
        branch = self.settings.get('branch', 'main')
        
        # Add token to URL if provided
        if token and 'github.com' in repo_url:
            repo_url = repo_url.replace('https://', f'https://{token}@')
        
        try:
            # Create parent directory if needed
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.local_path.exists() and (self.local_path / '.git').exists():
                # Repository exists, pull latest changes
                return self._pull_changes()
            else:
                # Clone repository
                return self._clone_repository(repo_url, branch)
                
        except Exception as e:
            return False, f"Operation failed: {str(e)}"
    
    def _clone_repository(self, repo_url: str, branch: str) -> Tuple[bool, str]:
        """Clone the repository"""
        try:
            # Remove directory if it exists but is not a git repo
            if self.local_path.exists():
                shutil.rmtree(self.local_path)
            
            cmd = ['git', 'clone', '-b', branch, repo_url, str(self.local_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Configure git user for commits
                self._configure_git_user()
                return True, "Repository cloned successfully"
            else:
                return False, f"Clone failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Clone error: {str(e)}"
    
    def _pull_changes(self) -> Tuple[bool, str]:
        """Pull latest changes from remote"""
        try:
            # First, check if there are uncommitted changes
            cmd = ['git', 'status', '--porcelain']
            result = subprocess.run(cmd, cwd=self.local_path, capture_output=True, text=True)
            
            if result.stdout.strip():
                return False, "Uncommitted changes in repository. Please commit or stash first."
            
            # Pull changes
            cmd = ['git', 'pull', 'origin', self.settings.get('branch', 'main')]
            result = subprocess.run(cmd, cwd=self.local_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, "Repository updated successfully"
            else:
                return False, f"Pull failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Pull error: {str(e)}"
    
    def commit_and_push(self, message: str, files: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Commit changes and push to remote"""
        if not self.local_path or not self.local_path.exists():
            return False, "Repository not cloned"
            
        try:
            # Add files
            if files:
                for file in files:
                    cmd = ['git', 'add', file]
                    subprocess.run(cmd, cwd=self.local_path, check=True)
            else:
                # Add all changes
                cmd = ['git', 'add', '-A']
                subprocess.run(cmd, cwd=self.local_path, check=True)
            
            # Check if there are changes to commit
            cmd = ['git', 'status', '--porcelain']
            result = subprocess.run(cmd, cwd=self.local_path, capture_output=True, text=True)
            
            if not result.stdout.strip():
                return True, "No changes to commit"
            
            # Commit
            cmd = ['git', 'commit', '-m', message]
            result = subprocess.run(cmd, cwd=self.local_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"Commit failed: {result.stderr}"
            
            # Push
            cmd = ['git', 'push', 'origin', self.settings.get('branch', 'main')]
            result = subprocess.run(cmd, cwd=self.local_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, "Changes pushed successfully"
            else:
                return False, f"Push failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Commit/push error: {str(e)}"
    
    def get_status(self) -> Tuple[bool, str]:
        """Get git status of the repository"""
        if not self.local_path or not self.local_path.exists():
            return False, "Repository not cloned"
            
        try:
            cmd = ['git', 'status', '--porcelain']
            result = subprocess.run(cmd, cwd=self.local_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                if result.stdout.strip():
                    return True, f"Uncommitted changes:\n{result.stdout}"
                else:
                    return True, "Working directory clean"
            else:
                return False, f"Status check failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Status error: {str(e)}"
    
    def list_presets(self) -> List[str]:
        """List all .sh files in the repository"""
        if not self.local_path or not self.local_path.exists():
            return []
            
        try:
            # Find all .sh files
            sh_files = []
            for file in self.local_path.rglob("*.sh"):
                # Get relative path from repo root
                rel_path = file.relative_to(self.local_path)
                sh_files.append(str(rel_path))
            
            return sorted(sh_files)
        except Exception:
            return []
    
    def get_preset_path(self, preset_name: str) -> Optional[Path]:
        """Get full path to a preset file"""
        if not self.local_path:
            return None
            
        preset_path = self.local_path / preset_name
        return preset_path if preset_path.exists() else None
    
    def save_preset(self, preset_name: str, content: str) -> Tuple[bool, str]:
        """Save a preset file to the repository"""
        if not self.local_path:
            return False, "Repository not configured"
            
        try:
            preset_path = self.local_path / preset_name
            
            # Create parent directories if needed
            preset_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            with open(preset_path, 'w') as f:
                f.write(content)
                
            return True, f"Preset saved: {preset_name}"
            
        except Exception as e:
            return False, f"Save error: {str(e)}"
    
    def _configure_git_user(self):
        """Configure git user for the repository"""
        try:
            # Set a default user if not configured
            subprocess.run(['git', 'config', 'user.name', 'VastAI Provisioning GUI'], 
                         cwd=self.local_path, check=True)
            subprocess.run(['git', 'config', 'user.email', 'vastai-gui@example.com'], 
                         cwd=self.local_path, check=True)
        except:
            pass  # Ignore errors, git might already be configured globally