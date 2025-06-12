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
    QSplitter, QGroupBox, QStackedWidget, QListWidgetItem, QMenu, QInputDialog
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
        self.load_btn = QPushButton("📂 Load Script")
        self.load_btn.setToolTip("Load a .sh script and check matching models in the database")
        self.load_btn.clicked.connect(self.load_script)
        
        self.save_btn = QPushButton("💾 Save Script")
        self.save_btn.setToolTip("Generate and save script with checked models")
        self.save_btn.clicked.connect(self.save_script)
        
        self.upload_btn = QPushButton("🚀 Upload to Git")
        self.upload_btn.setToolTip("Save script as default.sh and commit to git")
        self.upload_btn.clicked.connect(self.upload_to_git)
        
        # Presets button with dropdown menu
        self.presets_btn = QPushButton("📋 Presets ▼")
        self.presets_btn.setToolTip("Load saved preset configurations")
        self.presets_menu = QMenu()
        self.presets_btn.setMenu(self.presets_menu)
        
        # Clear all button
        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.setToolTip("Uncheck all models in the database")
        self.clear_btn.clicked.connect(self.clear_all_selections)
        
        header_layout.addWidget(self.load_btn)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.upload_btn)
        header_layout.addWidget(self.presets_btn)
        header_layout.addWidget(self.clear_btn)
        
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
        self.data_manager.load_presets()
        self.category_manager.refresh_ui_from_data()
        self._update_presets_menu()
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
        """Load a provisioning script"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Provisioning Script",
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
        """Save the generated script"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Provisioning Script",
            "provisioning.sh",
            "Shell Scripts (*.sh);;All Files (*)"
        )
        
        if filename:
            try:
                script = self.script_generator.generate_script(self.data_manager.data)
                with open(filename, 'w') as f:
                    f.write(script)
                
                # Make executable
                os.chmod(filename, 0o755)
                
                QMessageBox.information(self, "Success", f"Script saved to {filename}")
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
    
    def _update_presets_menu(self):
        """Update the presets dropdown menu"""
        self.presets_menu.clear()
        
        # Add "Save Current as Preset" option
        save_action = self.presets_menu.addAction("💾 Save Current as Preset...")
        save_action.triggered.connect(self._save_current_as_preset)
        
        self.presets_menu.addSeparator()
        
        # Add existing presets
        if self.data_manager.presets:
            for preset_name in sorted(self.data_manager.presets.keys()):
                preset_action = self.presets_menu.addAction(preset_name)
                preset_action.triggered.connect(
                    lambda checked=False, name=preset_name: self._load_preset(name)
                )
            
            self.presets_menu.addSeparator()
            
            # Add delete preset submenu
            delete_menu = self.presets_menu.addMenu("🗑️ Delete Preset")
            for preset_name in sorted(self.data_manager.presets.keys()):
                delete_action = delete_menu.addAction(preset_name)
                delete_action.triggered.connect(
                    lambda checked=False, name=preset_name: self._delete_preset(name)
                )
        else:
            no_presets_action = self.presets_menu.addAction("(No presets saved)")
            no_presets_action.setEnabled(False)
    
    def _save_current_as_preset(self):
        """Save the current configuration as a preset"""
        preset_name, ok = QInputDialog.getText(
            self,
            "Save Preset",
            "Enter preset name:",
            text=""
        )
        
        if not ok or not preset_name.strip():
            return
        
        preset_name = preset_name.strip()
        
        # Check if preset already exists
        overwrite = False
        if preset_name in self.data_manager.presets:
            reply = QMessageBox.question(
                self,
                "Overwrite Preset",
                f"Preset '{preset_name}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            overwrite = True
        
        if self.data_manager.create_preset(preset_name, overwrite):
            self.data_manager.save_presets()
            self._update_presets_menu()
            
            QMessageBox.information(
                self,
                "Preset Saved",
                f"Preset '{preset_name}' saved successfully!"
            )
    
    def _load_preset(self, preset_name):
        """Load a preset configuration"""
        reply = QMessageBox.question(
            self,
            "Load Preset",
            f"Loading preset '{preset_name}' will replace your current configuration. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        if self.data_manager.load_preset(preset_name):
            self.category_manager.refresh_ui_from_data()
            self._update_preview()
            self.data_manager.save_database()
            
            QMessageBox.information(
                self,
                "Preset Loaded",
                f"Preset '{preset_name}' loaded successfully!"
            )
    
    def _delete_preset(self, preset_name):
        """Delete a preset"""
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Are you sure you want to delete preset '{preset_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        if self.data_manager.delete_preset(preset_name):
            self.data_manager.save_presets()
            self._update_presets_menu()
            
            QMessageBox.information(
                self,
                "Preset Deleted",
                f"Preset '{preset_name}' deleted successfully!"
            )
    
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


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = ProvisioningGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()