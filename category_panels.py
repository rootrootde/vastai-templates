#!/usr/bin/env python3
"""
Category Panels Module

Handles creation and management of category panels in the GUI.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QTextEdit,
    QLabel, QGroupBox, QLineEdit, QCheckBox, QAbstractItemView, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QObject


class CategoryPanelManager(QObject):
    """Manages creation and interaction with category panels"""
    
    # Signals
    search_requested = Signal(str)
    data_changed = Signal()
    
    def __init__(self, stacked_widget, data_manager):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.data_manager = data_manager
        self.panels = {}
        self.list_widgets = {}
        self.input_widgets = {}
    
    def create_all_panels(self):
        """Create all category panels"""
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
        self.parallel_input.setText(str(self.data_manager.data.get('max_parallel_downloads', 4)))
        self.parallel_input.setMaximumWidth(100)
        self.parallel_input.setPlaceholderText("4")
        self.parallel_input.textChanged.connect(self._update_parallel_downloads)
        parallel_input_layout.addWidget(self.parallel_input)
        
        parallel_help = QLabel("(Set to 1 to disable parallel downloading)")
        parallel_help.setStyleSheet("color: gray; font-size: 10px;")
        parallel_input_layout.addWidget(parallel_help)
        parallel_input_layout.addStretch()
        
        parallel_layout.addLayout(parallel_input_layout)
        layout.addWidget(parallel_group)
        
        layout.addStretch()
        
        self.stacked_widget.addWidget(settings_widget)
        self.panels["settings"] = settings_widget
    
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
        add_btn.clicked.connect(lambda: self._add_items(key, text_input))
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
            search_btn.clicked.connect(lambda: self.search_requested.emit(key))
            button_layout.addWidget(search_btn)
        
        # Remove button
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(lambda: self._remove_items(key, list_widget))
        button_layout.addWidget(remove_btn)
        
        # Check all button
        check_all_btn = QPushButton("Check All")
        check_all_btn.clicked.connect(lambda: self._set_all_checked(key, list_widget, True))
        button_layout.addWidget(check_all_btn)
        
        # Uncheck all button
        uncheck_all_btn = QPushButton("Uncheck All")
        uncheck_all_btn.clicked.connect(lambda: self._set_all_checked(key, list_widget, False))
        button_layout.addWidget(uncheck_all_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Store references
        self.list_widgets[key] = list_widget
        self.input_widgets[key] = text_input
        self.panels[key] = panel_widget
        
        self.stacked_widget.addWidget(panel_widget)
    
    def _update_parallel_downloads(self):
        """Update the max parallel downloads setting"""
        try:
            value = int(self.parallel_input.text())
            if value >= 1:
                self.data_manager.update_max_parallel_downloads(value)
                self.data_changed.emit()
        except ValueError:
            # Invalid input, ignore
            pass
    
    def _add_items(self, key, text_input):
        """Add items from text input to the category"""
        text = text_input.toPlainText().strip()
        if not text:
            return
            
        # Split by newlines and add non-empty lines
        items = [line.strip() for line in text.split('\n') if line.strip()]
        
        list_widget = self.list_widgets[key]
        for item_text in items:
            if self.data_manager.add_item(key, item_text, checked=True):
                # Get the added item to get its display name
                all_items = self.data_manager.get_all_items(key)
                added_item = None
                for item in all_items:
                    if item['url'] == item_text:
                        added_item = item
                        break
                
                if added_item:
                    display_name = added_item.get('name') or added_item['url']
                    self._add_list_item_with_checkbox(list_widget, display_name, True, key, item_text)
        
        text_input.clear()
        self.data_changed.emit()
        self.data_manager.save_database()  # Auto-save database
    
    def _add_list_item_with_checkbox(self, list_widget, text, checked, key, url=None):
        """Add a list item with a checkbox"""
        item = QListWidgetItem()
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        
        # Use URL for tracking if provided, otherwise use text
        tracking_key = url if url else text
        checkbox.stateChanged.connect(
            lambda state: self._update_item_checked_state(key, tracking_key, state == Qt.Checked)
        )
        
        # Store the URL in the checkbox for later reference
        if url:
            checkbox.setProperty("url", url)
        
        list_widget.addItem(item)
        list_widget.setItemWidget(item, checkbox)
        item.setSizeHint(checkbox.sizeHint())
    
    def _update_item_checked_state(self, key, url, checked):
        """Update the checked state of an item in the data"""
        self.data_manager.update_item_checked_state(key, url, checked)
        self.data_changed.emit()
        self.data_manager.save_database()  # Auto-save when checkbox state changes
    
    def _set_all_checked(self, key, list_widget, checked_state):
        """Set all items in a category to checked or unchecked"""
        # Update data
        self.data_manager.set_all_checked(key, checked_state)
        
        # Update UI
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            checkbox = list_widget.itemWidget(item)
            if checkbox:
                checkbox.setChecked(checked_state)
        
        self.data_changed.emit()
    
    def _remove_items(self, key, list_widget):
        """Remove selected items from the category"""
        selected_items = list_widget.selectedItems()
        for item in selected_items:
            # Get checkbox widget
            checkbox = list_widget.itemWidget(item)
            if checkbox:
                # Get the URL from the stored property or use the text as fallback
                url = checkbox.property("url") or checkbox.text()
                # Remove from data
                self.data_manager.remove_item(key, url)
                list_widget.takeItem(list_widget.row(item))
        
        self.data_changed.emit()
        self.data_manager.save_database()  # Auto-save after removal
    
    def add_model_from_search(self, model_type, url):
        """Add a model URL from search results"""
        if model_type not in self.list_widgets:
            return False
            
        list_widget = self.list_widgets[model_type]
        
        if self.data_manager.add_item(model_type, url, checked=True):
            # Get the added item to get its display name
            all_items = self.data_manager.get_all_items(model_type)
            added_item = None
            for item in all_items:
                if item['url'] == url:
                    added_item = item
                    break
            
            if added_item:
                display_name = added_item.get('name') or added_item['url']
                self._add_list_item_with_checkbox(list_widget, display_name, True, model_type, url)
                self.data_changed.emit()
                self.data_manager.save_database()  # Auto-save after adding from search
                return True
        
        return False
    
    def refresh_ui_from_data(self):
        """Refresh all UI elements from the data"""
        # Update each category's list widget
        for key in self.data_manager.data:
            if key != 'max_parallel_downloads' and key in self.list_widgets:
                list_widget = self.list_widgets[key]
                list_widget.clear()
                
                for item in self.data_manager.get_all_items(key):
                    # Use stored name if available, otherwise fetch or use URL
                    display_name = item.get('name') or item['url']
                    if not item.get('name'):
                        # Try to fetch name if not stored (for backward compatibility)
                        from data_manager import fetch_model_metadata
                        fetched_name = fetch_model_metadata(item['url'])
                        if fetched_name:
                            item['name'] = fetched_name
                            display_name = fetched_name
                    
                    self._add_list_item_with_checkbox(
                        list_widget,
                        display_name,
                        item.get('checked', True),
                        key,
                        item['url']
                    )
        
        # Update parallel downloads setting
        if hasattr(self, 'parallel_input'):
            self.parallel_input.setText(str(self.data_manager.data.get('max_parallel_downloads', 4)))
    
    def get_category_index_map(self):
        """Get mapping of category keys to stacked widget indices"""
        return {
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