"""
Settings dialog for GitHub repository configuration
"""

import json
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal


class SettingsDialog(QDialog):
    """Dialog for configuring GitHub repository settings"""
    
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        # Settings file path
        self.settings_file = Path.home() / ".vastai-provisioning" / "settings.json"
        self.settings_file.parent.mkdir(exist_ok=True)
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Repository settings group
        repo_group = QGroupBox("Repository Settings")
        repo_layout = QFormLayout()
        
        self.repo_url_input = QLineEdit()
        self.repo_url_input.setPlaceholderText("https://github.com/username/presets-repo.git")
        repo_layout.addRow("Repository URL:", self.repo_url_input)
        
        self.branch_input = QLineEdit()
        self.branch_input.setPlaceholderText("main")
        self.branch_input.setText("main")
        repo_layout.addRow("Branch:", self.branch_input)
        
        repo_group.setLayout(repo_layout)
        layout.addWidget(repo_group)
        
        # Authentication settings group
        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout()
        
        self.github_token_input = QLineEdit()
        self.github_token_input.setEchoMode(QLineEdit.Password)
        self.github_token_input.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        auth_layout.addRow("GitHub Token:", self.github_token_input)
        
        # Token help
        token_help = QLabel('<a href="https://github.com/settings/tokens">Generate GitHub Token</a>')
        token_help.setOpenExternalLinks(True)
        auth_layout.addRow("", token_help)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # Local storage settings
        storage_group = QGroupBox("Local Storage")
        storage_layout = QFormLayout()
        
        self.local_path_input = QLineEdit()
        default_path = Path.home() / ".vastai-provisioning" / "presets-repo"
        self.local_path_input.setText(str(default_path))
        self.local_path_input.setReadOnly(True)
        storage_layout.addRow("Local Path:", self.local_path_input)
        
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)
        
        button_layout.addStretch()
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def load_settings(self):
        """Load settings from file"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.repo_url_input.setText(settings.get('repo_url', ''))
                    self.branch_input.setText(settings.get('branch', 'main'))
                    self.github_token_input.setText(settings.get('github_token', ''))
                    if 'local_path' in settings:
                        self.local_path_input.setText(settings['local_path'])
            except Exception as e:
                QMessageBox.warning(self, "Load Error", f"Failed to load settings: {e}")
    
    def save_settings(self):
        """Save settings to file"""
        settings = {
            'repo_url': self.repo_url_input.text().strip(),
            'branch': self.branch_input.text().strip() or 'main',
            'github_token': self.github_token_input.text().strip(),
            'local_path': self.local_path_input.text()
        }
        
        if not settings['repo_url']:
            QMessageBox.warning(self, "Validation Error", "Repository URL is required!")
            return
            
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.settings_changed.emit(settings)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}")
    
    def test_connection(self):
        """Test GitHub connection"""
        repo_url = self.repo_url_input.text().strip()
        token = self.github_token_input.text().strip()
        
        if not repo_url:
            QMessageBox.warning(self, "Test Failed", "Please enter a repository URL")
            return
            
        # Import GitHub integration module (will create next)
        try:
            from github_integration import GitHubIntegration
            github = GitHubIntegration()
            
            # Configure with current values
            settings = {
                'repo_url': repo_url,
                'github_token': token,
                'branch': self.branch_input.text() or 'main',
                'local_path': self.local_path_input.text()
            }
            
            if github.test_connection(settings):
                QMessageBox.information(self, "Success", "Successfully connected to repository!")
            else:
                QMessageBox.warning(self, "Failed", "Failed to connect to repository. Check URL and token.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection test failed: {e}")
    
    def get_settings(self):
        """Get current settings"""
        return {
            'repo_url': self.repo_url_input.text().strip(),
            'branch': self.branch_input.text().strip() or 'main',
            'github_token': self.github_token_input.text().strip(),
            'local_path': self.local_path_input.text()
        }