#!/usr/bin/env python3
"""
Vast.ai Provisioning Script Generator - Refactored

Advanced GUI for managing ComfyUI provisioning scripts with smart model identification.
This is a refactored version with better separation of concerns and modular design.

Key Features:
- 🗄️ Global Model Database: Persistent storage, never lose models when loading scripts
- 🎯 Smart Model Names: Auto-fetch metadata from CivitAI/Hugging Face with platform indicators
- 📋 Enhanced Presets: Save/load configurations without replacing database
- 🔍 Model Search: Built-in search for CivitAI and Hugging Face models
- 🎨 Platform Emojis: 🎨 CivitAI, 🤗 Hugging Face, 📁 GitHub visual identification

Usage:
    python provisioning_gui_refactored.py

Database:
    model_database.json - Persistent global model database
    presets.json - Saved preset configurations
"""

import sys
import os
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QTextEdit, QLabel, QFileDialog, QMessageBox, 
    QSplitter, QGroupBox, QStackedWidget, QListWidgetItem, QMenu, QInputDialog,
    QProgressDialog
)
from PySide6.QtCore import Qt

# Import our modular components
from model_search import ModelSearchDialog
from data_manager import DataManager
from script_utils import ScriptGenerator, ScriptParser
from category_panels import CategoryPanelManager


class ProvisioningGUI(QMainWindow):
    """Main GUI application for provisioning script generation"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vast.ai Provisioning Script Generator")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize modular components
        self.data_manager = DataManager()
        self.script_generator = ScriptGenerator()
        self.script_parser = ScriptParser()
        
        self.setup_ui()
        self._load_initial_data()
        
    def setup_ui(self):
        """Set up the main user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Header with buttons
        self._create_header(main_layout)
        
        # Create 3-part horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Category list
        self._create_category_list_panel(splitter)
        
        # Middle panel: URL management
        self._create_middle_panel(splitter)
        
        # Right panel: Preview
        self._create_preview_panel(splitter)
        
        splitter.setSizes([180, 500, 400])
        main_layout.addWidget(splitter)
        
    def _create_header(self, parent_layout):
        """Create the header with title and control buttons"""
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Vast.ai Provisioning Script Generator</h2>"))
        header_layout.addStretch()
        
        # Main action buttons
        self.load_btn = QPushButton("📂 Load Preset")
        self.load_btn.setToolTip("Load a .sh preset file and check matching models in the database")
        self.load_btn.clicked.connect(self.load_script)
        
        self.save_btn = QPushButton("💾 Save Preset")
        self.save_btn.setToolTip("Save current selection as a .sh preset file")
        self.save_btn.clicked.connect(self.save_script)
        
        self.upload_btn = QPushButton("🚀 Upload to Git")
        self.upload_btn.setToolTip("Save script as default.sh and commit to git")
        self.upload_btn.clicked.connect(self.upload_to_git)
        
        # Clear all button
        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.setToolTip("Uncheck all models in the database")
        self.clear_btn.clicked.connect(self.clear_all_selections)
        
        # Refresh model names button
        self.refresh_btn = QPushButton("🔄 Refresh Names")
        self.refresh_btn.setToolTip("Refresh model names from CivitAI and Hugging Face")
        self.refresh_btn.clicked.connect(self.refresh_model_names)
        
        header_layout.addWidget(self.load_btn)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.upload_btn)
        header_layout.addWidget(self.clear_btn)
        header_layout.addWidget(self.refresh_btn)
        
        parent_layout.addLayout(header_layout)
        
    def _create_category_list_panel(self, parent_splitter):
        """Create the left panel with category list"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        categories_label = QLabel("Categories")
        categories_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        left_layout.addWidget(categories_label)
        
        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(200)
        self.category_list.setMinimumWidth(150)
        
        # Populate category list
        self._populate_category_list()
        self.category_list.currentItemChanged.connect(self._on_category_changed)
        
        left_layout.addWidget(self.category_list)
        parent_splitter.addWidget(left_panel)
        
    def _create_middle_panel(self, parent_splitter):
        """Create the middle panel with category management"""
        self.middle_panel = QWidget()
        self.middle_layout = QVBoxLayout(self.middle_panel)
        self.middle_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create a stacked widget to hold all category panels
        self.stacked_widget = QStackedWidget()
        self.middle_layout.addWidget(self.stacked_widget)
        
        # Initialize category panel manager
        self.category_manager = CategoryPanelManager(self.stacked_widget, self.data_manager)
        self.category_manager.create_all_panels()
        
        # Connect signals
        self.category_manager.search_requested.connect(self._open_search_dialog)
        self.category_manager.data_changed.connect(self._update_preview)
        
        parent_splitter.addWidget(self.middle_panel)
        
    def _create_preview_panel(self, parent_splitter):
        """Create the right panel with script preview"""
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumWidth(400)
        preview_layout.addWidget(self.preview_text)
        
        parent_splitter.addWidget(preview_group)
        
    def _populate_category_list(self):
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
            
    def _on_category_changed(self, current, previous):
        """Handle category selection change"""
        if not current:
            return
            
        key = current.data(Qt.UserRole)
        if not key:
            return
            
        # Get index mapping from category manager
        index_map = self.category_manager.get_category_index_map()
        
        if key in index_map:
            self.stacked_widget.setCurrentIndex(index_map[key])
    
    def _load_initial_data(self):
        """Load initial data and update UI"""
        self.data_manager.load_database()
        self.category_manager.refresh_ui_from_data()
        self._update_preview()
    
    def _open_search_dialog(self, model_type):
        """Open the model search dialog"""
        if not hasattr(self, 'search_dialog') or not self.search_dialog:
            self.search_dialog = ModelSearchDialog()
            self.search_dialog.model_selected.connect(
                lambda url, platform: self._add_model_from_search(model_type, url, platform)
            )
            
        self.current_model_type = model_type
        self.search_dialog.show()
        self.search_dialog.raise_()
        self.search_dialog.activateWindow()
        
    def _add_model_from_search(self, model_type, url, platform):
        """Add a model URL from search results"""
        success = self.category_manager.add_model_from_search(model_type, url)
        
        if success:
            QMessageBox.information(
                self,
                "Model Added",
                f"Model URL added to {model_type.replace('_', ' ').title()}"
            )
        else:
            QMessageBox.warning(
                self,
                "Model Exists",
                "This model already exists in the database."
            )
    
    def _update_preview(self):
        """Update the script preview"""
        if not hasattr(self, 'preview_text'):
            return
        try:
            script = self.script_generator.generate_script(self.data_manager.data)
            self.preview_text.setPlainText(script)
        except FileNotFoundError as e:
            self.preview_text.setPlainText(f"Error: {e}")
    
    def load_script(self):
        """Load a provisioning script preset"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Preset",
            "",
            "Shell Scripts (*.sh);;All Files (*)"
        )
        
        if filename:
            with open(filename, 'r') as f:
                content = f.read()
                self.script_parser.parse_script(content, self.data_manager)
                self.category_manager.refresh_ui_from_data()
                self._update_preview()
                self.data_manager.save_database()
    
    def save_script(self):
        """Save the generated script preset"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Preset",
            "preset.sh",
            "Shell Scripts (*.sh);;All Files (*)"
        )
        
        if filename:
            try:
                # Force sync UI state to database before generating script
                self.category_manager.sync_ui_to_database()
                
                script = self.script_generator.generate_script(self.data_manager.data)
                with open(filename, 'w') as f:
                    f.write(script)
                
                # Make executable
                os.chmod(filename, 0o755)
                
                QMessageBox.information(self, "Success", f"Preset saved to {filename}")
            except FileNotFoundError as e:
                QMessageBox.critical(self, "Error", str(e))
    
    def clear_all_selections(self):
        """Clear all selections in the database"""
        reply = QMessageBox.question(
            self,
            "Clear All Selections",
            "This will uncheck all models in the database. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.data_manager.clear_all_selections()
            self.category_manager.refresh_ui_from_data()
            self._update_preview()
            self.data_manager.save_database()
    
    
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
            # Force sync UI state to database before generating script
            self.category_manager.sync_ui_to_database()
            
            # Save the script to default.sh
            script = self.script_generator.generate_script(self.data_manager.data)
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
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def refresh_model_names(self):
        """Refresh model names from CivitAI and Hugging Face"""
        reply = QMessageBox.question(
            self,
            "Refresh Model Names",
            "This will fetch the latest model names from CivitAI and Hugging Face.\n\n"
            "This may take a while if you have many models.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Create progress dialog
        progress = QProgressDialog("Refreshing model names...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Refreshing")
        progress.show()
        
        # Define progress callback
        def update_progress(current, total):
            if progress.wasCanceled():
                return False
            progress.setValue(int((current / total) * 100))
            progress.setLabelText(f"Refreshing model names... ({current}/{total})")
            QApplication.processEvents()
            return True
        
        try:
            # Refresh model names
            refreshed, total = self.data_manager.refresh_all_model_names(
                progress_callback=lambda c, t: update_progress(c, t) if not progress.wasCanceled() else False
            )
            
            progress.close()
            
            if refreshed == total:
                # Refresh the UI to show new names
                self.category_manager.refresh_ui_from_data()
                
                QMessageBox.information(
                    self,
                    "Refresh Complete",
                    f"Successfully refreshed {refreshed} model names!"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Refresh Cancelled",
                    f"Refresh cancelled. Updated {refreshed} out of {total} models."
                )
                
        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self,
                "Error",
                f"Error refreshing model names: {str(e)}"
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