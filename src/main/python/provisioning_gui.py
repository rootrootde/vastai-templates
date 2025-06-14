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
"""

import sys
import os
import json
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QTextEdit, QLabel, QFileDialog, QMessageBox, 
    QSplitter, QGroupBox, QStackedWidget, QInputDialog,
    QProgressDialog, QComboBox
)
from PySide6.QtCore import Qt

# Import our modular components
from model_search import ModelSearchDialog
from data_manager import DataManager
from script_utils import ScriptGenerator, ScriptParser
from category_panels import CategoryPanelManager
from settings_dialog import SettingsDialog
from github_integration import GitHubIntegration


class ProvisioningGUI(QMainWindow):
    """Main GUI application for provisioning script generation"""
    
    def __init__(self, app_context=None):
        super().__init__()
        self.setWindowTitle("Vast.ai Provisioning Script Generator")
        self.setGeometry(100, 100, 1000, 700)
        self.app_context = app_context
        
        # Initialize modular components
        self.data_manager = DataManager()
        
        # Pass app context to script generator for resource access
        if app_context:
            template_path = app_context.get_resource('template.sh')
            self.script_generator = ScriptGenerator(template_file=template_path)
        else:
            self.script_generator = ScriptGenerator()
            
        self.script_parser = ScriptParser()
        self.github_integration = GitHubIntegration()
        
        # Connect data manager with GitHub integration
        self.data_manager.set_github_integration(self.github_integration)
        
        # Load settings and configure GitHub
        self._load_github_settings()
        
        self.setup_ui()
        self._load_initial_data()
        
        # Check GitHub sync status on startup
        self._check_github_status()
        
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
        
        # GitHub Settings button
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setToolTip("Configure GitHub repository settings")
        self.settings_btn.clicked.connect(self.open_settings)
        
        # GitHub Sync button
        self.sync_btn = QPushButton("🔄 Sync")
        self.sync_btn.setToolTip("Pull latest presets from GitHub repository")
        self.sync_btn.clicked.connect(self.sync_with_github)
        
        # Preset dropdown
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.preset_combo.setToolTip("Select a preset to load")
        self.preset_combo.addItem("Select preset...")
        self.preset_combo.currentTextChanged.connect(self.on_preset_selected)
        
        # Main action buttons  
        self.load_btn = QPushButton("📂 Browse")
        self.load_btn.setToolTip("Browse for preset files")
        self.load_btn.clicked.connect(self.load_preset_from_repo)
        
        self.save_btn = QPushButton("💾 Save Preset")
        self.save_btn.setToolTip("Save current selection as a preset to GitHub repository")
        self.save_btn.clicked.connect(self.save_preset_to_repo)
        
        self.commit_push_btn = QPushButton("🚀 Commit & Push")
        self.commit_push_btn.setToolTip("Commit and push all changes to GitHub")
        self.commit_push_btn.clicked.connect(self.commit_and_push)
        
        # Clear all button
        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.setToolTip("Uncheck all models in the database")
        self.clear_btn.clicked.connect(self.clear_all_selections)
        
        # Refresh model names button
        self.refresh_btn = QPushButton("🔄 Refresh Names")
        self.refresh_btn.setToolTip("Refresh model names from CivitAI and Hugging Face")
        self.refresh_btn.clicked.connect(self.refresh_model_names)
        
        header_layout.addWidget(self.settings_btn)
        header_layout.addWidget(self.sync_btn)
        header_layout.addSpacing(20)
        header_layout.addWidget(QLabel("Preset:"))
        header_layout.addWidget(self.preset_combo)
        header_layout.addWidget(self.load_btn)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.commit_push_btn)
        header_layout.addSpacing(20)
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
            ("🔍 CLIP", "clip_models"),
            ("🎨 Style Models", "style_models"),
            ("🎨 PuLID", "pulid_models"),
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
        # Copy default database from app resources if local database doesn't exist
        if not self.data_manager.database_file.exists():
            # Try to get default database from fbs resources
            if self.app_context:
                try:
                    resource_db = self.app_context.get_resource('model_database.json')
                    import shutil
                    shutil.copy2(resource_db, self.data_manager.database_file)
                except Exception as e:
                    logging.warning(f"Could not copy default database: {e}")
        
        self.data_manager.load_database()
        self.category_manager.refresh_ui_from_data()
        self._update_preview()
        # Update preset dropdown
        self._update_preset_list()
    
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
                
                # Force save the database after sync
                self.data_manager.save_database()
                
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
    
    def _load_github_settings(self):
        """Load GitHub settings from configuration"""
        settings_file = Path.home() / ".vastai-provisioning" / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.github_integration.configure(settings)
            except Exception as e:
                logging.error(f"Error loading settings: {e}")
    
    def _check_github_status(self):
        """Check GitHub repository status"""
        if self.github_integration.settings:
            # Try to sync with GitHub on startup
            self.sync_with_github(silent=True)
            # Update preset list after sync
            self._update_preset_list()
    
    def open_settings(self):
        """Open the settings dialog"""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()
    
    def _on_settings_changed(self, settings):
        """Handle settings change"""
        self.github_integration.configure(settings)
        # Update data manager with new GitHub integration (database stays local)
        self.data_manager.set_github_integration(self.github_integration)
        # Sync with GitHub after settings change
        self.sync_with_github()
    
    def sync_with_github(self, silent=False):
        """Sync with GitHub repository"""
        if not self.github_integration.settings.get('repo_url'):
            if not silent:
                QMessageBox.warning(
                    self,
                    "Not Configured",
                    "Please configure GitHub settings first."
                )
            return
        
        # Clone or pull repository
        success, message = self.github_integration.clone_or_pull()
        
        if success:
            # Update data manager with GitHub integration (database stays local)
            self.data_manager.set_github_integration(self.github_integration)
            
            if not silent:
                QMessageBox.information(
                    self,
                    "Sync Complete", 
                    message
                )
            # Refresh the category list if needed
            self._update_preset_list()
        else:
            if not silent:
                QMessageBox.critical(
                    self,
                    "Sync Failed",
                    message
                )
    
    def load_preset_from_repo(self):
        """Load a preset from the GitHub repository"""
        # Get list of available presets
        presets = self.data_manager.list_available_presets()
        
        if not presets:
            QMessageBox.warning(
                self,
                "No Presets",
                "No preset files found in repository.\nPlease sync first."
            )
            return
        
        # Show selection dialog
        preset, ok = QInputDialog.getItem(
            self,
            "Load Preset",
            "Select a preset to load:",
            presets,
            0,
            False
        )
        
        if ok and preset:
            success, message = self.data_manager.load_preset_from_repo(preset)
            
            if success:
                # Refresh UI
                self.category_manager.refresh_ui_from_data()
                self._update_preview()
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.critical(self, "Error", message)
    
    def save_preset_to_repo(self):
        """Save current selection as a preset to GitHub repository"""
        # Get preset name
        filename, ok = QInputDialog.getText(
            self,
            "Save Preset",
            "Enter preset filename (e.g., 'sdxl-setup.sh'):",
            text="preset.sh"
        )
        
        if not ok or not filename:
            return
        
        # Ensure .sh extension
        if not filename.endswith('.sh'):
            filename += '.sh'
        
        # Force sync UI state
        self.category_manager.sync_ui_to_database()
        
        # Force save the database after sync
        self.data_manager.save_database()
        
        # Save preset (without immediate commit)
        success, message = self.data_manager.save_preset_to_repo(filename)
        
        if success:
            # Mark that we just saved this preset to prevent reload
            self._just_saved_preset = filename
            QMessageBox.information(self, "Success", message)
            # Update preset dropdown to include the new preset
            self._update_preset_list()
        else:
            QMessageBox.critical(self, "Error", message)
    
    def commit_and_push(self):
        """Commit and push all changes to GitHub"""
        # Check repository status
        success, status = self.github_integration.get_status()
        
        if not success:
            QMessageBox.critical(self, "Error", status)
            return
        
        if "Working directory clean" in status:
            QMessageBox.information(
                self,
                "No Changes",
                "No changes to commit."
            )
            return
        
        # Show status and get commit message
        commit_message, ok = QInputDialog.getText(
            self,
            "Commit Changes",
            f"Changes:\n{status}\n\nEnter commit message:",
            text="Update presets"
        )
        
        if not ok or not commit_message.strip():
            return
        
        # Commit and push
        success, message = self.github_integration.commit_and_push(commit_message.strip())
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
    
    def _update_preset_list(self):
        """Update the preset dropdown with available presets from GitHub repo only"""
        # Clear current items except the first one
        self.preset_combo.blockSignals(True)  # Prevent triggering selection events
        current_text = self.preset_combo.currentText()
        self.preset_combo.clear()
        self.preset_combo.addItem("Select preset...")
        
        # Get filtered preset list from data manager (excludes system files)
        presets = self.data_manager.list_available_presets()
        
        if presets:
            # Sort by filename and add to combo
            for preset_path in sorted(presets):
                filename = Path(preset_path).name
                self.preset_combo.addItem(filename, preset_path)
        
        # Restore previous selection if it still exists
        if current_text and current_text != "Select preset...":
            index = self.preset_combo.findText(current_text)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
        
        self.preset_combo.blockSignals(False)
    
    def on_preset_selected(self, preset_name):
        """Handle preset selection from dropdown"""
        if preset_name == "Select preset..." or not preset_name:
            return
        
        # Get the full preset path from combo data
        current_index = self.preset_combo.currentIndex()
        if current_index <= 0:
            return
            
        preset_path = self.preset_combo.itemData(current_index)
        if not preset_path:
            # Fallback - use the display name as path
            preset_path = preset_name
        
        # Don't reload if we just saved this preset
        if hasattr(self, '_just_saved_preset') and self._just_saved_preset == preset_path:
            self._just_saved_preset = None
            return
        
        # Load the selected preset
        success, message = self.data_manager.load_preset_from_repo(preset_path)
        
        if success:
            # Refresh UI
            self.category_manager.refresh_ui_from_data()
            self._update_preview()
            # Show brief status message
            self.statusBar().showMessage(f"Loaded preset: {preset_name}", 3000)
        else:
            # Reset dropdown to default and show error
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0)
            self.preset_combo.blockSignals(False)
            QMessageBox.critical(self, "Error", f"Failed to load preset: {message}")
    
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