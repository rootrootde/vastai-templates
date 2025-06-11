#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QListWidget, QPushButton, QTextEdit, QLineEdit,
    QLabel, QFileDialog, QMessageBox, QSplitter, QGroupBox,
    QAbstractItemView, QProgressBar, QScrollArea, QFrame,
    QComboBox, QCheckBox, QDialog, QFormLayout, QSpinBox,
    QDialogButtonBox, QInputDialog
)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QPixmap
import subprocess
import json
import requests
import urllib.parse
from datetime import datetime
import base64
import configparser

class SearchWorker(QThread):
    results_ready = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, platform, query, model_type):
        super().__init__()
        self.platform = platform
        self.query = query
        self.model_type = model_type
        
    def run(self):
        try:
            if self.platform == "civitai":
                results = self.search_civitai()
            elif self.platform == "huggingface":
                results = self.search_huggingface()
            else:
                results = []
            self.results_ready.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))
            
    def search_civitai(self):
        """Search CivitAI models"""
        url = "https://civitai.com/api/v1/models"
        params = {
            "query": self.query,
            "limit": 20,
            "sort": "Highest Rated"
        }
        
        # Map model types to CivitAI types
        type_mapping = {
            "checkpoint_models": "Checkpoint",
            "lora_models": "LORA",
            "vae_models": "VAE",
            "controlnet_models": "ControlNet",
            "upscale_models": "Upscaler"
        }
        
        if self.model_type in type_mapping:
            params["types"] = type_mapping[self.model_type]
            
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for item in data.get("items", []):
            # Get the latest version
            versions = item.get("modelVersions", [])
            if not versions:
                continue
                
            latest_version = versions[0]
            files = latest_version.get("files", [])
            
            # Find primary file
            primary_file = None
            for file in files:
                if file.get("primary", False):
                    primary_file = file
                    break
            
            if not primary_file:
                continue
                
            download_url = primary_file.get("downloadUrl")
            if not download_url:
                continue
                
            results.append({
                "title": item.get("name", "Unknown"),
                "author": item.get("creator", {}).get("username", "Unknown"),
                "description": item.get("description", "")[:200] + "..." if len(item.get("description", "")) > 200 else item.get("description", ""),
                "download_url": download_url,
                "rating": item.get("stats", {}).get("rating", 0),
                "downloads": item.get("stats", {}).get("downloadCount", 0),
                "type": item.get("type", "Unknown"),
                "platform": "civitai",
                "image_url": latest_version.get("images", [{}])[0].get("url") if latest_version.get("images") else None
            })
            
        return results
        
    def search_huggingface(self):
        """Search Hugging Face models"""
        url = "https://huggingface.co/api/models"
        params = {
            "search": self.query,
            "limit": 20,
            "sort": "downloads",
            "direction": -1
        }
        
        # Map model types to HF tags
        tag_mapping = {
            "checkpoint_models": "diffusers",
            "lora_models": "lora",
            "controlnet_models": "controlnet",
            "vae_models": "vae"
        }
        
        if self.model_type in tag_mapping:
            params["filter"] = tag_mapping[self.model_type]
            
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for item in data:
            # Construct download URL for git clone or direct file access
            model_id = item.get("modelId", "")
            if not model_id:
                continue
                
            # For most models, we'll use the git clone URL
            download_url = f"https://huggingface.co/{model_id}"
            
            results.append({
                "title": model_id.split("/")[-1] if "/" in model_id else model_id,
                "author": model_id.split("/")[0] if "/" in model_id else "Unknown",
                "description": item.get("pipeline_tag", "") + " - " + ", ".join(item.get("tags", [])[:3]),
                "download_url": download_url,
                "downloads": item.get("downloads", 0),
                "likes": item.get("likes", 0),
                "type": item.get("pipeline_tag", "Unknown"),
                "platform": "huggingface",
                "last_modified": item.get("lastModified", "")
            })
            
        return results


class ModelSearchDialog(QWidget):
    model_selected = Signal(str, str)  # url, platform
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Models")
        self.setFixedSize(800, 600)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Search controls
        search_layout = QHBoxLayout()
        
        # Platform selection
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["CivitAI", "Hugging Face"])
        search_layout.addWidget(QLabel("Platform:"))
        search_layout.addWidget(self.platform_combo)
        
        # Model type selection
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "All Types", "Checkpoints", "LoRA", "VAE", 
            "ControlNet", "Upscale Models"
        ])
        search_layout.addWidget(QLabel("Type:"))
        search_layout.addWidget(self.type_combo)
        
        layout.addLayout(search_layout)
        
        # Search input
        search_input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search terms...")
        self.search_input.returnPressed.connect(self.search_models)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_models)
        
        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(self.search_btn)
        layout.addLayout(search_input_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results area
        self.results_scroll = QScrollArea()
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_scroll.setWidget(self.results_widget)
        self.results_scroll.setWidgetResizable(True)
        layout.addWidget(self.results_scroll)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
    def search_models(self):
        query = self.search_input.text().strip()
        if not query:
            return
            
        platform = self.platform_combo.currentText().lower().replace(" ", "")
        model_type = self.get_model_type()
        
        # Clear previous results
        for i in reversed(range(self.results_layout.count())):
            self.results_layout.itemAt(i).widget().setParent(None)
            
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.search_btn.setEnabled(False)
        
        # Start search worker
        self.search_worker = SearchWorker(platform, query, model_type)
        self.search_worker.results_ready.connect(self.display_results)
        self.search_worker.error_occurred.connect(self.handle_error)
        self.search_worker.start()
        
    def get_model_type(self):
        type_text = self.type_combo.currentText()
        type_mapping = {
            "Checkpoints": "checkpoint_models",
            "LoRA": "lora_models",
            "VAE": "vae_models",
            "ControlNet": "controlnet_models",
            "Upscale Models": "upscale_models"
        }
        return type_mapping.get(type_text, "")
        
    def display_results(self, results):
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        
        if not results:
            label = QLabel("No results found.")
            self.results_layout.addWidget(label)
            return
            
        for result in results:
            result_widget = self.create_result_widget(result)
            self.results_layout.addWidget(result_widget)
            
    def create_result_widget(self, result):
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet("QFrame { border: 1px solid #ccc; margin: 2px; padding: 4px; }")
        
        layout = QVBoxLayout(frame)
        
        # Title and author
        title_layout = QHBoxLayout()
        title_label = QLabel(f"<b>{result['title']}</b>")
        author_label = QLabel(f"by {result['author']}")
        author_label.setStyleSheet("color: #666;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(author_label)
        title_layout.addStretch()
        
        # Stats
        stats_text = ""
        if result['platform'] == 'civitai':
            stats_text = f"★ {result['rating']:.1f} | ↓ {result['downloads']:,}"
        else:
            stats_text = f"♥ {result['likes']} | ↓ {result['downloads']:,}"
            
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet("color: #666; font-size: 10px;")
        title_layout.addWidget(stats_label)
        
        layout.addLayout(title_layout)
        
        # Description
        if result['description']:
            desc_label = QLabel(result['description'])
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #333; font-size: 11px;")
            layout.addWidget(desc_label)
            
        # Add button
        add_btn = QPushButton("Add to Script")
        add_btn.clicked.connect(lambda: self.model_selected.emit(result['download_url'], result['platform']))
        layout.addWidget(add_btn)
        
        return frame
        
    def handle_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Search Error", f"Search failed: {error_msg}")


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 400)
        self.settings_file = Path.home() / ".vastai_provisioning_settings.ini"
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # GitHub Settings Group
        github_group = QGroupBox("GitHub Settings")
        github_layout = QFormLayout(github_group)
        
        # GitHub Token
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("Enter your GitHub Personal Access Token")
        github_layout.addRow("GitHub Token:", self.token_input)
        
        # Repository Owner
        self.owner_input = QLineEdit()
        self.owner_input.setPlaceholderText("e.g., your-username")
        github_layout.addRow("Repository Owner:", self.owner_input)
        
        # Repository Name
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("e.g., vastai-templates")
        github_layout.addRow("Repository Name:", self.repo_input)
        
        # Branch
        self.branch_input = QLineEdit()
        self.branch_input.setText("main")
        self.branch_input.setPlaceholderText("main")
        github_layout.addRow("Branch:", self.branch_input)
        
        # Default Path
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("e.g., templates/ (optional)")
        github_layout.addRow("Upload Path:", self.path_input)
        
        layout.addWidget(github_group)
        
        # API Settings Group
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout(api_group)
        
        # Request timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 60)
        self.timeout_spin.setValue(10)
        self.timeout_spin.setSuffix(" seconds")
        api_layout.addRow("Request Timeout:", self.timeout_spin)
        
        layout.addWidget(api_group)
        
        # Help text
        help_text = QLabel(
            "<b>GitHub Token Setup:</b><br>"
            "1. Go to GitHub → Settings → Developer settings → Personal access tokens<br>"
            "2. Generate a new token with 'repo' permissions<br>"
            "3. Copy and paste the token above<br><br>"
            "<b>Repository Format:</b><br>"
            "Owner: your GitHub username or organization<br>"
            "Name: the repository name (without .git)<br>"
            "Upload Path: optional subfolder in the repository"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; font-size: 10px; padding: 10px;")
        layout.addWidget(help_text)
        
        # Test connection button
        test_btn = QPushButton("Test GitHub Connection")
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def load_settings(self):
        """Load settings from file"""
        if not self.settings_file.exists():
            return
            
        config = configparser.ConfigParser()
        config.read(self.settings_file)
        
        if 'github' in config:
            github = config['github']
            self.token_input.setText(github.get('token', ''))
            self.owner_input.setText(github.get('owner', ''))
            self.repo_input.setText(github.get('repo', ''))
            self.branch_input.setText(github.get('branch', 'main'))
            self.path_input.setText(github.get('path', ''))
            
        if 'api' in config:
            api = config['api']
            self.timeout_spin.setValue(int(api.get('timeout', 10)))
            
    def save_settings(self):
        """Save settings to file"""
        config = configparser.ConfigParser()
        
        config['github'] = {
            'token': self.token_input.text(),
            'owner': self.owner_input.text(),
            'repo': self.repo_input.text(),
            'branch': self.branch_input.text(),
            'path': self.path_input.text()
        }
        
        config['api'] = {
            'timeout': str(self.timeout_spin.value())
        }
        
        with open(self.settings_file, 'w') as f:
            config.write(f)
            
    def get_settings(self):
        """Get current settings as dict"""
        return {
            'github': {
                'token': self.token_input.text(),
                'owner': self.owner_input.text(),
                'repo': self.repo_input.text(),
                'branch': self.branch_input.text(),
                'path': self.path_input.text()
            },
            'api': {
                'timeout': self.timeout_spin.value()
            }
        }
        
    def test_connection(self):
        """Test GitHub API connection"""
        token = self.token_input.text().strip()
        owner = self.owner_input.text().strip()
        repo = self.repo_input.text().strip()
        
        if not all([token, owner, repo]):
            QMessageBox.warning(self, "Missing Information", 
                              "Please fill in GitHub token, owner, and repository name.")
            return
            
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Test repository access
            url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_data = response.json()
                QMessageBox.information(
                    self, "Connection Successful", 
                    f"Successfully connected to repository:\n"
                    f"Name: {repo_data.get('full_name')}\n"
                    f"Description: {repo_data.get('description', 'No description')}\n"
                    f"Private: {repo_data.get('private', False)}"
                )
            elif response.status_code == 404:
                QMessageBox.critical(
                    self, "Repository Not Found", 
                    f"Repository '{owner}/{repo}' not found or not accessible.\n"
                    "Please check the owner and repository name."
                )
            elif response.status_code == 401:
                QMessageBox.critical(
                    self, "Authentication Failed", 
                    "Invalid GitHub token. Please check your token and try again."
                )
            else:
                QMessageBox.critical(
                    self, "Connection Failed", 
                    f"Failed to connect: {response.status_code}\n{response.text}"
                )
                
        except requests.RequestException as e:
            QMessageBox.critical(
                self, "Connection Error", 
                f"Failed to connect to GitHub: {str(e)}"
            )
            
    def accept(self):
        """Save settings and close dialog"""
        self.save_settings()
        super().accept()


class GitHubUploader:
    def __init__(self, settings):
        self.settings = settings
        
    def upload_file(self, content, filename, commit_message=None):
        """Upload file content to GitHub repository"""
        github = self.settings['github']
        token = github['token']
        owner = github['owner']
        repo = github['repo']
        branch = github['branch']
        path = github['path']
        
        if not all([token, owner, repo]):
            raise ValueError("Missing required GitHub settings")
            
        # Construct file path
        file_path = filename
        if path:
            file_path = f"{path.rstrip('/')}/{filename}"
            
        # Default commit message
        if not commit_message:
            commit_message = f"Update {filename} via Provisioning GUI"
            
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Check if file exists to get SHA for updates
        get_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        get_params = {'ref': branch}
        
        try:
            get_response = requests.get(get_url, headers=headers, params=get_params, 
                                      timeout=self.settings['api']['timeout'])
            file_sha = None
            if get_response.status_code == 200:
                file_sha = get_response.json().get('sha')
        except requests.RequestException:
            file_sha = None
            
        # Prepare upload data
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            'message': commit_message,
            'content': content_b64,
            'branch': branch
        }
        
        if file_sha:
            data['sha'] = file_sha
            
        # Upload file
        put_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        response = requests.put(put_url, headers=headers, json=data, 
                              timeout=self.settings['api']['timeout'])
        
        if response.status_code in [200, 201]:
            result = response.json()
            return {
                'success': True,
                'url': result['content']['html_url'],
                'message': 'File uploaded successfully'
            }
        else:
            return {
                'success': False,
                'error': f"Upload failed: {response.status_code} - {response.text}"
            }
            
    def list_files(self, path=""):
        """List files in repository path"""
        github = self.settings['github']
        token = github['token']
        owner = github['owner']
        repo = github['repo']
        branch = github['branch']
        
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {'ref': branch}
        
        response = requests.get(url, headers=headers, params=params,
                              timeout=self.settings['api']['timeout'])
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to list files: {response.status_code} - {response.text}")


class ProvisioningGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vast.ai Provisioning Script Generator")
        self.setGeometry(100, 100, 1000, 700)
        
        # Data storage
        self.data = {
            'apt_packages': [],
            'pip_packages': [],
            'nodes': [],
            'checkpoint_models': [],
            'unet_models': [],
            'lora_models': [],
            'vae_models': [],
            'esrgan_models': [],
            'upscale_models': [],
            'controlnet_models': [],
            'annotator_models': [],
            'clip_vision_models': []
        }
        
        self.setup_ui()
        self.load_default_script()
        
    def setup_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Vast.ai Provisioning Script Generator</h2>"))
        header_layout.addStretch()
        
        # Buttons
        self.load_btn = QPushButton("Load Script")
        self.load_btn.clicked.connect(self.load_script)
        self.save_btn = QPushButton("Save Script")
        self.save_btn.clicked.connect(self.save_script)
        self.upload_btn = QPushButton("Upload to Git")
        self.upload_btn.clicked.connect(self.upload_to_git)
        
        # Settings button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        
        header_layout.addWidget(self.settings_btn)
        header_layout.addWidget(self.load_btn)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.upload_btn)
        
        main_layout.addLayout(header_layout)
        
        # Splitter for tabs and preview
        splitter = QSplitter(Qt.Horizontal)
        
        # Tab widget for categories
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.update_preview)
        
        # Create tabs for each category
        self.create_category_tab("APT Packages", "apt_packages")
        self.create_category_tab("PIP Packages", "pip_packages")
        self.create_category_tab("ComfyUI Nodes", "nodes")
        self.create_category_tab("Checkpoints", "checkpoint_models")
        self.create_category_tab("UNET Models", "unet_models")
        self.create_category_tab("LoRA Models", "lora_models")
        self.create_category_tab("VAE Models", "vae_models")
        self.create_category_tab("ESRGAN Models", "esrgan_models")
        self.create_category_tab("Upscale Models", "upscale_models")
        self.create_category_tab("ControlNet", "controlnet_models")
        self.create_category_tab("Annotators", "annotator_models")
        self.create_category_tab("CLIP Vision", "clip_vision_models")
        
        splitter.addWidget(self.tabs)
        
        # Preview pane
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumWidth(400)
        preview_layout.addWidget(self.preview_text)
        
        splitter.addWidget(preview_group)
        splitter.setSizes([600, 400])
        
        main_layout.addWidget(splitter)
        
        # Initial preview
        self.update_preview()
        
    def create_category_tab(self, name, key):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Instructions
        if key == "apt_packages":
            layout.addWidget(QLabel("Enter APT package names (one per line)"))
        elif key == "pip_packages":
            layout.addWidget(QLabel("Enter Python package names (one per line)"))
        elif key == "nodes":
            layout.addWidget(QLabel("Enter ComfyUI node GitHub URLs (one per line)"))
        else:
            layout.addWidget(QLabel(f"Enter {name} URLs (one per line)"))
        
        # Input area
        input_layout = QHBoxLayout()
        
        # Text input for adding items
        text_input = QTextEdit()
        text_input.setMaximumHeight(100)
        text_input.setPlaceholderText("Paste URLs or package names here...")
        input_layout.addWidget(text_input)
        
        # Add button
        add_btn = QPushButton("Add")
        add_btn.setMaximumWidth(80)
        add_btn.clicked.connect(lambda: self.add_items(key, text_input))
        input_layout.addWidget(add_btn)
        
        layout.addLayout(input_layout)
        
        # List widget
        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(list_widget)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Search button (only for model categories)
        if key not in ['apt_packages', 'pip_packages', 'nodes']:
            search_btn = QPushButton("Search Models")
            search_btn.clicked.connect(lambda: self.open_search_dialog(key))
            button_layout.addWidget(search_btn)
        
        # Remove button
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(lambda: self.remove_items(key, list_widget))
        button_layout.addWidget(remove_btn)
        
        layout.addLayout(button_layout)
        
        # Store references
        setattr(self, f"{key}_list", list_widget)
        setattr(self, f"{key}_input", text_input)
        
        self.tabs.addTab(tab, name)
        
    def add_items(self, key, text_input):
        text = text_input.toPlainText().strip()
        if not text:
            return
            
        # Split by newlines and add non-empty lines
        items = [line.strip() for line in text.split('\n') if line.strip()]
        
        list_widget = getattr(self, f"{key}_list")
        for item in items:
            if item not in self.data[key]:
                self.data[key].append(item)
                list_widget.addItem(item)
        
        text_input.clear()
        self.update_preview()
        
    def open_search_dialog(self, model_type):
        """Open the model search dialog"""
        if not hasattr(self, 'search_dialog') or not self.search_dialog:
            self.search_dialog = ModelSearchDialog()
            self.search_dialog.model_selected.connect(self.add_model_from_search)
            
        self.current_model_type = model_type
        self.search_dialog.show()
        self.search_dialog.raise_()
        self.search_dialog.activateWindow()
        
    def add_model_from_search(self, url, platform):
        """Add a model URL from search results"""
        if hasattr(self, 'current_model_type') and self.current_model_type:
            model_type = self.current_model_type
            list_widget = getattr(self, f"{model_type}_list")
            
            if url not in self.data[model_type]:
                self.data[model_type].append(url)
                list_widget.addItem(url)
                self.update_preview()
                
        # Show success message
        QMessageBox.information(
            self,
            "Model Added",
            f"Model URL added to {self.current_model_type.replace('_', ' ').title()}"
        )
        
    def load_app_settings(self):
        """Load application settings"""
        settings_file = Path.home() / ".vastai_provisioning_settings.ini"
        if not settings_file.exists():
            return
            
        config = configparser.ConfigParser()
        config.read(settings_file)
        
        self.settings = {
            'github': {},
            'api': {'timeout': 10}
        }
        
        if 'github' in config:
            self.settings['github'] = dict(config['github'])
            
        if 'api' in config:
            self.settings['api'] = dict(config['api'])
            self.settings['api']['timeout'] = int(self.settings['api'].get('timeout', 10))
            
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
        
    def remove_items(self, key, list_widget):
        selected_items = list_widget.selectedItems()
        for item in selected_items:
            self.data[key].remove(item.text())
            list_widget.takeItem(list_widget.row(item))
        
        self.update_preview()
        
    def update_preview(self):
        if not hasattr(self, 'preview_text'):
            return
        script = self.generate_script()
        self.preview_text.setPlainText(script)
        
    def generate_script(self):
        template = '''#!/bin/bash

source /venv/main/bin/activate
COMFYUI_DIR=${{WORKSPACE}}/ComfyUI

# Packages are installed after nodes so we can fix them...

APT_PACKAGES=(
{apt_packages}
)

PIP_PACKAGES=(
{pip_packages}
)

NODES=(
{nodes}
)

WORKFLOWS=(

)

CHECKPOINT_MODELS=(
{checkpoint_models}
)

UNET_MODELS=(
{unet_models}
)

LORA_MODELS=(
{lora_models}
)

VAE_MODELS=(
{vae_models}
)

ESRGAN_MODELS=(
{esrgan_models}
)

UPSCALE_MODELS=(
{upscale_models}
)

CONTROLNET_MODELS=(
{controlnet_models}
)

ANNOTATOR_MODELS=(
{annotator_models}
)

CLIP_VISION_MODELS=(
{clip_vision_models}
)


function provisioning_start() {{
    provisioning_print_header
    provisioning_get_apt_packages
    provisioning_get_nodes
    provisioning_get_pip_packages
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/checkpoints" \\
        "${{CHECKPOINT_MODELS[@]}}"
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/unet" \\
        "${{UNET_MODELS[@]}}"
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/lora" \\
        "${{LORA_MODELS[@]}}"
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/controlnet" \\
        "${{CONTROLNET_MODELS[@]}}"
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/vae" \\
        "${{VAE_MODELS[@]}}"
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/esrgan" \\
        "${{ESRGAN_MODELS[@]}}"
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/upscale_models" \\
        "${{UPSCALE_MODELS[@]}}"
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/annotators" \\
        "${{ANNOTATOR_MODELS[@]}}"
    provisioning_get_files \\
        "${{COMFYUI_DIR}}/models/clip_vision" \\
        "${{CLIP_VISION_MODELS[@]}}"
    provisioning_print_end
}}

function provisioning_get_apt_packages() {{
    if [[ -n $APT_PACKAGES ]]; then
            sudo $APT_INSTALL ${{APT_PACKAGES[@]}}
    fi
}}

function provisioning_get_pip_packages() {{
    if [[ -n $PIP_PACKAGES ]]; then
            pip install --no-cache-dir ${{PIP_PACKAGES[@]}}
    fi
}}

function provisioning_get_nodes() {{
    for repo in "${{NODES[@]}}"; do
        dir="${{repo##*/}}"
        path="${{COMFYUI_DIR}}/custom_nodes/${{dir}}"
        requirements="${{path}}/requirements.txt"
        if [[ -d $path ]]; then
            if [[ ${{AUTO_UPDATE,,}} != "false" ]]; then
                printf "Updating node: %s...\\n" "${{repo}}"
                ( cd "$path" && git pull )
                if [[ -e $requirements ]]; then
                   pip install --no-cache-dir -r "$requirements"
                fi
            fi
        else
            printf "Downloading node: %s...\\n" "${{repo}}"
            git clone "${{repo}}" "${{path}}" --recursive
            if [[ -e $requirements ]]; then
                pip install --no-cache-dir -r "${{requirements}}"
            fi
        fi
    done
}}

function provisioning_get_files() {{
    if [[ -z $2 ]]; then return 1; fi
    
    dir="$1"
    mkdir -p "$dir"
    shift
    arr=("$@")
    printf "Downloading %s model(s) to %s...\\n" "${{#arr[@]}}" "$dir"
    for url in "${{arr[@]}}"; do
        printf "Downloading: %s\\n" "${{url}}"
        provisioning_download "${{url}}" "${{dir}}"
        printf "\\n"
    done
}}

function provisioning_print_header() {{
    printf "\\n##############################################\\n#                                            #\\n#          Provisioning container            #\\n#                                            #\\n#         This will take some time           #\\n#                                            #\\n# Your container will be ready on completion #\\n#                                            #\\n##############################################\\n\\n"
}}

function provisioning_print_end() {{
    printf "\\nProvisioning complete:  Application will start now\\n\\n"
}}

function provisioning_has_valid_hf_token() {{
    [[ -n "$HF_TOKEN" ]] || return 1
    url="https://huggingface.co/api/whoami-v2"

    response=$(curl -o /dev/null -s -w "%{{http_code}}" -X GET "$url" \\
        -H "Authorization: Bearer $HF_TOKEN" \\
        -H "Content-Type: application/json")

    # Check if the token is valid
    if [ "$response" -eq 200 ]; then
        return 0
    else
        return 1
    fi
}}

function provisioning_has_valid_civitai_token() {{
    [[ -n "$CIVITAI_TOKEN" ]] || return 1
    url="https://civitai.com/api/v1/models?hidden=1&limit=1"

    response=$(curl -o /dev/null -s -w "%{{http_code}}" -X GET "$url" \\
        -H "Authorization: Bearer $CIVITAI_TOKEN" \\
        -H "Content-Type: application/json")

    # Check if the token is valid
    if [ "$response" -eq 200 ]; then
        return 0
    else
        return 1
    fi
}}

# Download from $1 URL to $2 file path
function provisioning_download() {{
    if [[ -n $HF_TOKEN && $1 =~ ^https://([a-zA-Z0-9_-]+\\.)?huggingface\\.co(/|$|\\?) ]]; then
        auth_token="$HF_TOKEN"
    elif 
        [[ -n $CIVITAI_TOKEN && $1 =~ ^https://([a-zA-Z0-9_-]+\\.)?civitai\\.com(/|$|\\?) ]]; then
        auth_token="$CIVITAI_TOKEN"
    fi
    if [[ -n $auth_token ]];then
        wget --header="Authorization: Bearer $auth_token" -qnc --content-disposition --show-progress -e dotbytes="${{3:-4M}}" -P "$2" "$1"
    else
        wget -qnc --content-disposition --show-progress -e dotbytes="${{3:-4M}}" -P "$2" "$1"
    fi
}}

# Allow user to disable provisioning if they started with a script they didn't want
if [[ ! -f /.noprovisioning ]]; then
    provisioning_start
fi'''
        
        # Format the arrays
        def format_array(items):
            if not items:
                return ""
            return '\n'.join(f'    "{item}"' for item in items)
        
        # Fill in the template
        formatted_script = template.format(
            apt_packages=format_array(self.data.get('apt_packages', [])),
            pip_packages=format_array(self.data.get('pip_packages', [])),
            nodes=format_array(self.data.get('nodes', [])),
            checkpoint_models=format_array(self.data.get('checkpoint_models', [])),
            unet_models=format_array(self.data.get('unet_models', [])),
            lora_models=format_array(self.data.get('lora_models', [])),
            vae_models=format_array(self.data.get('vae_models', [])),
            esrgan_models=format_array(self.data.get('esrgan_models', [])),
            upscale_models=format_array(self.data.get('upscale_models', [])),
            controlnet_models=format_array(self.data.get('controlnet_models', [])),
            annotator_models=format_array(self.data.get('annotator_models', [])),
            clip_vision_models=format_array(self.data.get('clip_vision_models', []))
        )
        
        return formatted_script
        
    def load_default_script(self):
        """Load the existing default.sh script"""
        try:
            with open('default.sh', 'r') as f:
                content = f.read()
                self.parse_script(content)
        except FileNotFoundError:
            pass
            
    def parse_script(self, content):
        """Parse a bash script to extract arrays"""
        import re
        
        # Initialize settings
        self.settings = None
        self.load_app_settings()
        
        # Clear existing data
        for key in self.data:
            self.data[key] = []
            list_widget = getattr(self, f"{key}_list", None)
            if list_widget:
                list_widget.clear()
        
        # Define patterns for each array
        patterns = {
            'apt_packages': r'APT_PACKAGES=\((.*?)\)',
            'pip_packages': r'PIP_PACKAGES=\((.*?)\)',
            'nodes': r'NODES=\((.*?)\)',
            'checkpoint_models': r'CHECKPOINT_MODELS=\((.*?)\)',
            'unet_models': r'UNET_MODELS=\((.*?)\)',
            'lora_models': r'LORA_MODELS=\((.*?)\)',
            'vae_models': r'VAE_MODELS=\((.*?)\)',
            'esrgan_models': r'ESRGAN_MODELS=\((.*?)\)',
            'upscale_models': r'UPSCALE_MODELS=\((.*?)\)',
            'controlnet_models': r'CONTROLNET_MODELS=\((.*?)\)',
            'annotator_models': r'ANNOTATOR_MODELS=\((.*?)\)',
            'clip_vision_models': r'CLIP_VISION_MODELS=\((.*?)\)'
        }
        
        # Extract items from each array
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL)
            if match:
                array_content = match.group(1)
                # Extract quoted strings
                items = re.findall(r'"([^"]+)"', array_content)
                self.data[key] = items
                
                # Update UI
                list_widget = getattr(self, f"{key}_list", None)
                if list_widget:
                    for item in items:
                        list_widget.addItem(item)
        
        self.update_preview()
        
    def load_script(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Provisioning Script",
            "",
            "Shell Scripts (*.sh);;All Files (*)"
        )
        
        if filename:
            with open(filename, 'r') as f:
                content = f.read()
                self.parse_script(content)
                
    def save_script(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Provisioning Script",
            "provisioning.sh",
            "Shell Scripts (*.sh);;All Files (*)"
        )
        
        if filename:
            script = self.generate_script()
            with open(filename, 'w') as f:
                f.write(script)
            
            # Make executable
            os.chmod(filename, 0o755)
            
            QMessageBox.information(self, "Success", f"Script saved to {filename}")
            
    def upload_to_git(self):
        """Upload script directly to GitHub or use local git"""
        # Check if GitHub settings are configured
        if (self.settings and 
            self.settings.get('github', {}).get('token') and 
            self.settings.get('github', {}).get('owner') and 
            self.settings.get('github', {}).get('repo')):
            
            self.upload_to_github()
        else:
            # Fallback to local git method
            self.upload_to_local_git()
            
    def upload_to_github(self):
        """Upload script directly to GitHub via API"""
        # Get filename
        filename, ok = QInputDialog.getText(
            self,
            "GitHub Upload",
            "Enter filename for the script:",
            text="provisioning.sh"
        )
        
        if not filename or not ok:
            return
            
        if not filename.endswith('.sh'):
            filename += '.sh'
            
        # Get commit message
        commit_message, ok = QInputDialog.getText(
            self,
            "Commit Message",
            "Enter commit message:",
            text=f"Add provisioning script: {filename}"
        )
        
        if not ok:
            return
            
        try:
            # Generate script content
            script_content = self.generate_script()
            
            # Upload to GitHub
            uploader = GitHubUploader(self.settings)
            result = uploader.upload_file(script_content, filename, commit_message)
            
            if result['success']:
                QMessageBox.information(
                    self,
                    "Upload Successful",
                    f"Script uploaded successfully to GitHub!\n"
                    f"File: {filename}\n"
                    f"URL: {result['url']}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Upload Failed",
                    f"Failed to upload to GitHub:\n{result['error']}"
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Upload Error",
                f"Failed to upload to GitHub: {str(e)}"
            )
            
    def upload_to_local_git(self):
        """Upload using local git (original method)"""
        # Check if we're in a git repository
        try:
            subprocess.run(['git', 'status'], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error", 
                               "GitHub settings not configured and not in a git repository!\n\n"
                               "Please either:\n"
                               "1. Configure GitHub settings via Settings button, or\n"
                               "2. Run this tool from within a git repository")
            return
            
        # Get filename
        filename, ok = QFileDialog.getSaveFileName(
            self,
            "Save and Upload Script",
            "provisioning.sh",
            "Shell Scripts (*.sh)"
        )
        
        if not filename or not ok:
            return
            
        # Save the script
        script = self.generate_script()
        with open(filename, 'w') as f:
            f.write(script)
        os.chmod(filename, 0o755)
        
        try:
            # Git add
            subprocess.run(['git', 'add', filename], check=True)
            
            # Git commit
            commit_message = f"Add provisioning script: {os.path.basename(filename)}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Git push
            result = subprocess.run(['git', 'push'], capture_output=True, text=True)
            
            if result.returncode == 0:
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Script uploaded successfully!\nFile: {filename}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Push Failed",
                    f"Commit successful but push failed:\n{result.stderr}\n\nYou can push manually later."
                )
                
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Git operation failed: {str(e)}"
            )

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = ProvisioningGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()