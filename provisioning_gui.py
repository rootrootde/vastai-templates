#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QTextEdit, QLineEdit,
    QLabel, QFileDialog, QMessageBox, QSplitter, QGroupBox,
    QAbstractItemView, QProgressBar, QScrollArea, QFrame,
    QComboBox, QCheckBox, QInputDialog, QStackedWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal
import subprocess
import requests
import urllib.parse
from datetime import datetime

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
                "description": item.get("description", "")[:200] + "..." if len(item.get("description", "")) > 200 else item.get("description", ""),
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
            "ControlNet", "Upscale Models", "Workflows",
            "Text Encoders", "Diffusion Models"
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
            "Upscale Models": "upscale_models",
            "Workflows": "workflows",
            "Text Encoders": "text_encoder_models",
            "Diffusion Models": "diffusion_models"
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


class ProvisioningGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vast.ai Provisioning Script Generator")
        self.setGeometry(100, 100, 1000, 700)
        
        # Data storage - now stores items as {url: str, checked: bool}
        self.data = {
            'apt_packages': [],
            'pip_packages': [],
            'nodes': [],
            'workflows': [],
            'checkpoint_models': [],
            'unet_models': [],
            'lora_models': [],
            'vae_models': [],
            'esrgan_models': [],
            'upscale_models': [],
            'controlnet_models': [],
            'annotator_models': [],
            'clip_vision_models': [],
            'text_encoder_models': [],
            'diffusion_models': [],
            'max_parallel_downloads': 4
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
        
        header_layout.addWidget(self.load_btn)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.upload_btn)
        
        main_layout.addLayout(header_layout)
        
        # Create 3-part horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Category list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        categories_label = QLabel("Categories")
        categories_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        left_layout.addWidget(categories_label)
        
        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(200)
        self.category_list.setMinimumWidth(150)
        
        left_layout.addWidget(self.category_list)
        splitter.addWidget(left_panel)
        
        # Middle panel: URL management
        self.middle_panel = QWidget()
        self.middle_layout = QVBoxLayout(self.middle_panel)
        self.middle_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create a stacked widget to hold all category panels
        self.stacked_widget = QStackedWidget()
        self.middle_layout.addWidget(self.stacked_widget)
        
        # Create panels for each category
        self.create_category_panels()
        
        splitter.addWidget(self.middle_panel)
        
        # Now that stacked_widget exists, we can populate and connect
        self.populate_category_list()
        self.category_list.currentItemChanged.connect(self.on_category_changed)
        
        # Preview pane
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumWidth(400)
        preview_layout.addWidget(self.preview_text)
        
        splitter.addWidget(preview_group)
        splitter.setSizes([180, 500, 400])
        
        main_layout.addWidget(splitter)
        
        # Initial preview
        self.update_preview()
        
    
    
    def populate_category_list(self):
        """Populate the category list with all available categories"""
        categories = [
            ("⚙️ Settings", "settings"),
            ("📦 APT Packages", "apt_packages"),
            ("📦 PIP Packages", "pip_packages"),
            ("🔧 ComfyUI Nodes", "nodes"),
            ("🔧 Workflows", "workflows"),
            ("🎯 Checkpoints", "checkpoint_models"),
            ("🎯 UNET Models", "unet_models"),
            ("🎯 Diffusion Models", "diffusion_models"),
            ("🎨 LoRA Models", "lora_models"),
            ("🎨 VAE Models", "vae_models"),
            ("🎨 ControlNet", "controlnet_models"),
            ("⬆️ ESRGAN Models", "esrgan_models"),
            ("⬆️ Upscale Models", "upscale_models"),
            ("🔍 Annotators", "annotator_models"),
            ("🔍 CLIP Vision", "clip_vision_models"),
            ("🔍 Text Encoders", "text_encoder_models"),
        ]
        
        for display_name, key in categories:
            self.category_list.addItem(display_name)
            self.category_list.item(self.category_list.count() - 1).setData(Qt.UserRole, key)
        
        # Select first item by default
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)
    
    def create_category_panels(self):
        """Create panels for each category in the stacked widget"""
        # Settings panel
        self.create_settings_panel()
        
        # Create panels for each model category
        category_configs = [
            ("apt_packages", "APT Packages", "Enter APT package names (one per line)"),
            ("pip_packages", "PIP Packages", "Enter Python package names (one per line)"),
            ("nodes", "ComfyUI Nodes", "Enter ComfyUI node GitHub URLs (one per line)"),
            ("workflows", "Workflows", "Enter workflow URLs (one per line)"),
            ("checkpoint_models", "Checkpoints", "Enter Checkpoint URLs (one per line)"),
            ("unet_models", "UNET Models", "Enter UNET Model URLs (one per line)"),
            ("diffusion_models", "Diffusion Models", "Enter Diffusion Model URLs (one per line)"),
            ("lora_models", "LoRA Models", "Enter LoRA Model URLs (one per line)"),
            ("vae_models", "VAE Models", "Enter VAE Model URLs (one per line)"),
            ("controlnet_models", "ControlNet", "Enter ControlNet URLs (one per line)"),
            ("esrgan_models", "ESRGAN Models", "Enter ESRGAN Model URLs (one per line)"),
            ("upscale_models", "Upscale Models", "Enter Upscale Model URLs (one per line)"),
            ("annotator_models", "Annotators", "Enter Annotator URLs (one per line)"),
            ("clip_vision_models", "CLIP Vision", "Enter CLIP Vision URLs (one per line)"),
            ("text_encoder_models", "Text Encoders", "Enter Text Encoder URLs (one per line)"),
        ]
        
        for key, name, instructions in category_configs:
            self.create_category_panel(key, name, instructions)
    
    def create_settings_panel(self):
        """Create the settings panel"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # Title
        title = QLabel("Settings")
        title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Parallel downloads setting
        parallel_group = QGroupBox("Download Settings")
        parallel_layout = QVBoxLayout(parallel_group)
        
        parallel_label = QLabel("Maximum Parallel Downloads:")
        parallel_layout.addWidget(parallel_label)
        
        parallel_input_layout = QHBoxLayout()
        self.parallel_input = QLineEdit()
        self.parallel_input.setText(str(self.data.get('max_parallel_downloads', 4)))
        self.parallel_input.setMaximumWidth(100)
        self.parallel_input.setPlaceholderText("4")
        self.parallel_input.textChanged.connect(self.update_parallel_downloads)
        parallel_input_layout.addWidget(self.parallel_input)
        
        parallel_help = QLabel("(Set to 1 to disable parallel downloading)")
        parallel_help.setStyleSheet("color: gray; font-size: 10px;")
        parallel_input_layout.addWidget(parallel_help)
        parallel_input_layout.addStretch()
        
        parallel_layout.addLayout(parallel_input_layout)
        layout.addWidget(parallel_group)
        
        layout.addStretch()
        
        self.stacked_widget.addWidget(settings_widget)
        
    def create_category_panel(self, key, name, instructions):
        """Create a panel for a single category"""
        panel_widget = QWidget()
        layout = QVBoxLayout(panel_widget)
        
        # Title
        title = QLabel(name)
        title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 5px;")
        layout.addWidget(title)
        
        # Instructions
        instructions_label = QLabel(instructions)
        instructions_label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 10px;")
        layout.addWidget(instructions_label)
        
        # Input area
        input_layout = QHBoxLayout()
        
        # Text input for adding items
        text_input = QTextEdit()
        text_input.setMaximumHeight(120)
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
        
        # Search button (only for model categories and workflows)
        if key not in ['apt_packages', 'pip_packages', 'nodes']:
            if key == 'workflows':
                search_btn = QPushButton("Search Workflows")
            else:
                search_btn = QPushButton("Search Models")
            search_btn.clicked.connect(lambda: self.open_search_dialog(key))
            button_layout.addWidget(search_btn)
        
        # Remove button
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(lambda: self.remove_items(key, list_widget))
        button_layout.addWidget(remove_btn)
        
        # Check all button
        check_all_btn = QPushButton("Check All")
        check_all_btn.clicked.connect(lambda: self.set_all_checked(key, list_widget, True))
        button_layout.addWidget(check_all_btn)
        
        # Uncheck all button
        uncheck_all_btn = QPushButton("Uncheck All")
        uncheck_all_btn.clicked.connect(lambda: self.set_all_checked(key, list_widget, False))
        button_layout.addWidget(uncheck_all_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Store references
        setattr(self, f"{key}_list", list_widget)
        setattr(self, f"{key}_input", text_input)
        
        self.stacked_widget.addWidget(panel_widget)
    
    def on_category_changed(self, current, previous):
        """Handle category selection change"""
        if not current:
            return
            
        key = current.data(Qt.UserRole)
        if not key:
            return
            
        # Map keys to stacked widget indices
        index_map = {
            "settings": 0,
            "apt_packages": 1,
            "pip_packages": 2,
            "nodes": 3,
            "workflows": 4,
            "checkpoint_models": 5,
            "unet_models": 6,
            "diffusion_models": 7,
            "lora_models": 8,
            "vae_models": 9,
            "controlnet_models": 10,
            "esrgan_models": 11,
            "upscale_models": 12,
            "annotator_models": 13,
            "clip_vision_models": 14,
            "text_encoder_models": 15,
        }
        
        if key in index_map:
            self.stacked_widget.setCurrentIndex(index_map[key])
    
    
    def update_parallel_downloads(self):
        """Update the max parallel downloads setting"""
        try:
            value = int(self.parallel_input.text())
            if value >= 1:
                self.data['max_parallel_downloads'] = value
                self.update_preview()
        except ValueError:
            # Invalid input, ignore
            pass
        
    def add_items(self, key, text_input):
        text = text_input.toPlainText().strip()
        if not text:
            return
            
        # Split by newlines and add non-empty lines
        items = [line.strip() for line in text.split('\n') if line.strip()]
        
        list_widget = getattr(self, f"{key}_list")
        for item_text in items:
            # Check if item already exists
            exists = any(item['url'] == item_text for item in self.data[key])
            if not exists:
                # Add to data with checked=True by default
                self.data[key].append({'url': item_text, 'checked': True})
                # Create list item with checkbox
                self.add_list_item_with_checkbox(list_widget, item_text, True, key)
        
        text_input.clear()
        self.update_preview()
    
    def add_list_item_with_checkbox(self, list_widget, text, checked, key):
        """Add a list item with a checkbox"""
        item = QListWidgetItem()
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.stateChanged.connect(lambda state: self.update_item_checked_state(key, text, state == Qt.Checked))
        
        list_widget.addItem(item)
        list_widget.setItemWidget(item, checkbox)
        item.setSizeHint(checkbox.sizeHint())
    
    def update_item_checked_state(self, key, url, checked):
        """Update the checked state of an item in the data"""
        for item in self.data[key]:
            if item['url'] == url:
                item['checked'] = checked
                break
        self.update_preview()
    
    def set_all_checked(self, key, list_widget, checked):
        """Set all items in a category to checked or unchecked"""
        # Update data
        for item in self.data[key]:
            item['checked'] = checked
        
        # Update UI
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            checkbox = list_widget.itemWidget(item)
            if checkbox:
                checkbox.setChecked(checked)
        
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
            
            # Check if URL already exists
            exists = any(item['url'] == url for item in self.data[model_type])
            if not exists:
                # Add to data with checked=True by default
                self.data[model_type].append({'url': url, 'checked': True})
                # Create list item with checkbox
                self.add_list_item_with_checkbox(list_widget, url, True, model_type)
                self.update_preview()
                
        # Show success message
        QMessageBox.information(
            self,
            "Model Added",
            f"Model URL added to {self.current_model_type.replace('_', ' ').title()}"
        )
        
        
    def remove_items(self, key, list_widget):
        selected_items = list_widget.selectedItems()
        for item in selected_items:
            # Get checkbox widget
            checkbox = list_widget.itemWidget(item)
            if checkbox:
                url = checkbox.text()
                # Remove from data
                self.data[key] = [i for i in self.data[key] if i['url'] != url]
                list_widget.takeItem(list_widget.row(item))
        
        self.update_preview()
        
    def update_preview(self):
        if not hasattr(self, 'preview_text'):
            return
        script = self.generate_script()
        self.preview_text.setPlainText(script)
        
    def generate_script(self):
        # Load template from file
        try:
            with open('template.sh', 'r') as f:
                template = f.read()
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "Template file 'template.sh' not found!")
            return ""
        
        # Format the arrays - only include checked items
        def format_array(items):
            if not items:
                return ""
            # Filter to only checked items
            checked_urls = [item['url'] for item in items if item.get('checked', True)]
            if not checked_urls:
                return ""
            return '\n'.join(f'    "{url}"' for url in checked_urls)
        
        # Replace placeholders using string replacement
        replacements = {
            '{apt_packages}': format_array(self.data.get('apt_packages', [])),
            '{pip_packages}': format_array(self.data.get('pip_packages', [])),
            '{nodes}': format_array(self.data.get('nodes', [])),
            '{workflows}': format_array(self.data.get('workflows', [])),
            '{checkpoint_models}': format_array(self.data.get('checkpoint_models', [])),
            '{unet_models}': format_array(self.data.get('unet_models', [])),
            '{lora_models}': format_array(self.data.get('lora_models', [])),
            '{vae_models}': format_array(self.data.get('vae_models', [])),
            '{esrgan_models}': format_array(self.data.get('esrgan_models', [])),
            '{upscale_models}': format_array(self.data.get('upscale_models', [])),
            '{controlnet_models}': format_array(self.data.get('controlnet_models', [])),
            '{annotator_models}': format_array(self.data.get('annotator_models', [])),
            '{clip_vision_models}': format_array(self.data.get('clip_vision_models', [])),
            '{text_encoder_models}': format_array(self.data.get('text_encoder_models', [])),
            '{diffusion_models}': format_array(self.data.get('diffusion_models', [])),
            '{max_parallel_downloads}': str(self.data.get('max_parallel_downloads', 4))
        }
        
        # Apply replacements
        formatted_script = template
        for placeholder, value in replacements.items():
            formatted_script = formatted_script.replace(placeholder, value)
        
        return formatted_script
        
    def load_default_script(self):
        """Load the existing provisioning.sh script"""
        try:
            with open('provisioning.sh', 'r') as f:
                content = f.read()
                self.parse_script(content)
        except FileNotFoundError:
            pass
            
    def parse_script(self, content):
        """Parse a bash script to extract arrays and settings"""
        import re
        
        # Clear existing data
        for key in self.data:
            if key == 'max_parallel_downloads':
                self.data[key] = 4  # Reset to default
            else:
                self.data[key] = []
                list_widget = getattr(self, f"{key}_list", None)
                if list_widget:
                    list_widget.clear()
        
        # Define patterns for each array
        patterns = {
            'apt_packages': r'APT_PACKAGES=\((.*?)\)',
            'pip_packages': r'PIP_PACKAGES=\((.*?)\)',
            'nodes': r'NODES=\((.*?)\)',
            'workflows': r'WORKFLOWS=\((.*?)\)',
            'checkpoint_models': r'CHECKPOINT_MODELS=\((.*?)\)',
            'unet_models': r'UNET_MODELS=\((.*?)\)',
            'lora_models': r'LORA_MODELS=\((.*?)\)',
            'vae_models': r'VAE_MODELS=\((.*?)\)',
            'esrgan_models': r'ESRGAN_MODELS=\((.*?)\)',
            'upscale_models': r'UPSCALE_MODELS=\((.*?)\)',
            'controlnet_models': r'CONTROLNET_MODELS=\((.*?)\)',
            'annotator_models': r'ANNOTATOR_MODELS=\((.*?)\)',
            'clip_vision_models': r'CLIP_VISION_MODELS=\((.*?)\)',
            'text_encoder_models': r'TEXT_ENCODER_MODELS=\((.*?)\)',
            'diffusion_models': r'DIFFUSION_MODELS=\((.*?)\)'
        }
        
        # Extract items from each array
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL)
            if match:
                array_content = match.group(1)
                # Extract quoted strings
                items = re.findall(r'"([^"]+)"', array_content)
                # Convert to new format with checked=True by default
                self.data[key] = [{'url': url, 'checked': True} for url in items]
                
                # Update UI
                list_widget = getattr(self, f"{key}_list", None)
                if list_widget:
                    for url in items:
                        self.add_list_item_with_checkbox(list_widget, url, True, key)
        
        # Parse MAX_PARALLEL_DOWNLOADS setting
        max_parallel_match = re.search(r'MAX_PARALLEL_DOWNLOADS=(\d+)', content)
        if max_parallel_match:
            try:
                max_parallel_value = int(max_parallel_match.group(1))
                self.data['max_parallel_downloads'] = max_parallel_value
                # Update UI if the input field exists
                if hasattr(self, 'parallel_input'):
                    self.parallel_input.setText(str(max_parallel_value))
            except ValueError:
                # If parsing fails, keep default value
                pass
        
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
        """Save and commit all changes to git"""
        # Check if we're in a git repository
        try:
            subprocess.run(['git', 'status'], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error", "Not in a git repository!")
            return
            
        # Get commit message
        commit_message, ok = QInputDialog.getText(
            self,
            "Commit Message",
            "Enter commit message:",
            text="Update provisioning script via GUI"
        )
        
        if not ok or not commit_message.strip():
            return
            
        try:
            # Save the script to default.sh
            script = self.generate_script()
            with open('default.sh', 'w') as f:
                f.write(script)
            os.chmod('default.sh', 0o755)
            
            # Git add all changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Git commit
            subprocess.run(['git', 'commit', '-m', commit_message.strip()], check=True)
            
            # Git push
            result = subprocess.run(['git', 'push'], capture_output=True, text=True)
            
            if result.returncode == 0:
                QMessageBox.information(
                    self, 
                    "Success", 
                    "Changes committed and pushed successfully!"
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