#!/usr/bin/env python3
"""
Model Search Module

Handles searching for models on CivitAI and Hugging Face platforms.
"""

import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QPushButton,
    QLabel, QProgressBar, QScrollArea, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal


class SearchWorker(QThread):
    """Worker thread for searching models on different platforms"""
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
            "sort": "Most Downloaded"
        }
        
        # Map model types to CivitAI types
        type_mapping = {
            "checkpoint_models": "Checkpoint",
            "lora_models": "LORA",
            "vae_models": "VAE",
            "controlnet_models": "ControlNet",
            "upscale_models": "Upscaler",
            "workflows": "Workflows",
            "text_encoder_models": "TextualInversion",
            "diffusion_models": "Checkpoint"
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
            
            # Find primary file or workflow file
            primary_file = None
            for file in files:
                if file.get("primary", False):
                    primary_file = file
                    break
            
            # If no primary file, look for workflow files (.json)
            if not primary_file and self.model_type == "workflows":
                for file in files:
                    if file.get("name", "").endswith(".json"):
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
                "description": self._truncate_text(item.get("description", ""), 200),
                "download_url": download_url,
                "rating": item.get("stats", {}).get("rating", 0),
                "downloads": item.get("stats", {}).get("downloadCount", 0),
                "type": item.get("type", "Unknown"),
                "platform": "civitai",
                "image_url": latest_version.get("images", [{}])[0].get("url") if latest_version.get("images") else None
            })
        
        # Sort by download count (descending)
        results.sort(key=lambda x: x.get('downloads', 0), reverse=True)
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
        
        # Sort by download count (descending)  
        results.sort(key=lambda x: x.get('downloads', 0), reverse=True)
        return results
    
    def _truncate_text(self, text, max_length):
        """Truncate text with ellipsis if too long"""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text


class ModelSearchDialog(QWidget):
    """Dialog for searching and selecting models from various platforms"""
    model_selected = Signal(str, str)  # url, platform
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Models")
        self.setFixedSize(800, 600)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Search controls
        self._create_search_controls(layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results area
        self._create_results_area(layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
    def _create_search_controls(self, parent_layout):
        """Create the search control widgets"""
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
            "ControlNet", "Upscale Models", "Workflows",
            "Text Encoders", "Diffusion Models"
        ])
        search_layout.addWidget(QLabel("Type:"))
        search_layout.addWidget(self.type_combo)
        
        parent_layout.addLayout(search_layout)
        
        # Search input
        search_input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search terms...")
        self.search_input.returnPressed.connect(self.search_models)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_models)
        
        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(self.search_btn)
        parent_layout.addLayout(search_input_layout)
        
    def _create_results_area(self, parent_layout):
        """Create the results display area"""
        self.results_scroll = QScrollArea()
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_scroll.setWidget(self.results_widget)
        self.results_scroll.setWidgetResizable(True)
        parent_layout.addWidget(self.results_scroll)
        
    def search_models(self):
        """Start a model search"""
        query = self.search_input.text().strip()
        if not query:
            return
            
        platform = self.platform_combo.currentText().lower().replace(" ", "")
        model_type = self._get_model_type()
        
        # Clear previous results
        self._clear_results()
            
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.search_btn.setEnabled(False)
        
        # Start search worker
        self.search_worker = SearchWorker(platform, query, model_type)
        self.search_worker.results_ready.connect(self.display_results)
        self.search_worker.error_occurred.connect(self.handle_error)
        self.search_worker.start()
        
    def _get_model_type(self):
        """Map UI model type selection to internal type"""
        type_text = self.type_combo.currentText()
        type_mapping = {
            "Checkpoints": "checkpoint_models",
            "LoRA": "lora_models",
            "VAE": "vae_models",
            "ControlNet": "controlnet_models",
            "Upscale Models": "upscale_models",
            "Workflows": "workflows",
            "Text Encoders": "text_encoder_models",
            "Diffusion Models": "diffusion_models"
        }
        return type_mapping.get(type_text, "")
    
    def _clear_results(self):
        """Clear previous search results"""
        for i in reversed(range(self.results_layout.count())):
            self.results_layout.itemAt(i).widget().setParent(None)
        
    def display_results(self, results):
        """Display search results in the UI"""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        
        if not results:
            label = QLabel("No results found.")
            self.results_layout.addWidget(label)
            return
            
        for result in results:
            result_widget = self._create_result_widget(result)
            self.results_layout.addWidget(result_widget)
            
    def _create_result_widget(self, result):
        """Create a widget for displaying a single search result"""
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
        stats_text = self._format_stats(result)
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
    
    def _format_stats(self, result):
        """Format stats text based on platform"""
        if result['platform'] == 'civitai':
            return f"★ {result['rating']:.1f} | ↓ {result['downloads']:,}"
        else:
            return f"♥ {result['likes']} | ↓ {result['downloads']:,}"
        
    def handle_error(self, error_msg):
        """Handle search errors"""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Search Error", f"Search failed: {error_msg}")