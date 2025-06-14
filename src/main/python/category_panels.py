#!/usr/bin/env python3
"""
Category Panels Module

Handles creation and management of category panels in the GUI.
"""

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QGroupBox, QLineEdit, QCheckBox, QAbstractItemView,
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QMessageBox
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
        self.tree_widgets = {}  # Changed from list_widgets to tree_widgets
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
            ("clip_models", "CLIP", "Enter CLIP Model URLs (one per line)"),
            ("style_models", "Style Models", "Enter Style Model URLs (one per line)"),
            ("pulid_models", "PuLID", "Enter PuLID Model URLs (one per line)"),
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
        
        # Tree widget for hierarchical display
        tree_widget = QTreeWidget()
        tree_widget.setHeaderHidden(True)
        tree_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        tree_widget.setDragDropMode(QAbstractItemView.DragDrop)
        tree_widget.setDefaultDropAction(Qt.MoveAction)
        tree_widget.setDropIndicatorShown(True)
        tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        tree_widget.customContextMenuRequested.connect(lambda pos: self._show_context_menu(key, tree_widget, pos))
        
        # Connect item changed signal for checkbox handling
        tree_widget.itemChanged.connect(self._on_tree_item_changed)
        layout.addWidget(tree_widget)
        
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
        
        # Create folder button
        create_folder_btn = QPushButton("📁 Create Folder")
        create_folder_btn.clicked.connect(lambda: self._create_new_folder(key, tree_widget))
        button_layout.addWidget(create_folder_btn)
        
        # Remove button
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(lambda: self._remove_items(key, tree_widget))
        button_layout.addWidget(remove_btn)
        
        # Check all button
        check_all_btn = QPushButton("Check All")
        check_all_btn.clicked.connect(lambda: self._set_all_checked(key, tree_widget, True))
        button_layout.addWidget(check_all_btn)
        
        # Uncheck all button
        uncheck_all_btn = QPushButton("Uncheck All")
        uncheck_all_btn.clicked.connect(lambda: self._set_all_checked(key, tree_widget, False))
        button_layout.addWidget(uncheck_all_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Store references
        self.tree_widgets[key] = tree_widget
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
        
        tree_widget = self.tree_widgets[key]
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
                    self._add_tree_item_with_checkbox(tree_widget, display_name, True, key, item_text, added_item.get('folder', ''), block_signals=False)
        
        text_input.clear()
        self.data_changed.emit()
        self.data_manager.save_database()  # Auto-save database
    
    def _add_tree_item_with_checkbox(self, tree_widget, text, checked, key, url=None, folder_path="", block_signals=False):
        """Add a tree item with a checkbox, handling folder hierarchy"""
        # If no folder path, add to root
        if not folder_path:
            item = QTreeWidgetItem(tree_widget)
            item.setText(0, text)
            item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            # Store metadata
            item.setData(0, Qt.UserRole, {"url": url or text, "category": key, "type": "model"})
            
            # Connect to state change
            if not block_signals:
                tree_widget.itemChanged.connect(self._on_tree_item_changed)
        else:
            # Find or create folder structure
            folder_item = self._find_or_create_folder(tree_widget, folder_path, key)
            
            # Add model to folder
            model_item = QTreeWidgetItem(folder_item)
            model_item.setText(0, text)
            model_item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            model_item.setFlags(model_item.flags() | Qt.ItemIsUserCheckable)
            
            # Store metadata
            model_item.setData(0, Qt.UserRole, {"url": url or text, "category": key, "type": "model"})
            
            # Update folder tri-state
            self._update_folder_tri_state(folder_item)
            
            # Connect to state change
            if not block_signals:
                tree_widget.itemChanged.connect(self._on_tree_item_changed)
    
    def _find_or_create_folder(self, tree_widget, folder_path, category):
        """Find or create a folder in the tree structure"""
        parts = folder_path.split("/")
        current_parent = tree_widget.invisibleRootItem()
        
        # Build folder path step by step
        current_path = ""
        for part in parts:
            current_path = current_path + "/" + part if current_path else part
            
            # Look for existing folder
            folder_item = None
            for i in range(current_parent.childCount()):
                child = current_parent.child(i)
                child_data = child.data(0, Qt.UserRole)
                if (child_data and child_data.get("type") == "folder" and 
                    child_data.get("folder_path") == current_path):
                    folder_item = child
                    break
            
            # Create folder if it doesn't exist
            if not folder_item:
                folder_item = QTreeWidgetItem(current_parent)
                folder_item.setText(0, f"📁 {part}")
                folder_item.setCheckState(0, Qt.Unchecked)
                folder_item.setFlags(folder_item.flags() | Qt.ItemIsUserCheckable)
                
                # Store folder metadata
                folder_item.setData(0, Qt.UserRole, {
                    "type": "folder",
                    "folder_path": current_path,
                    "category": category
                })
                
                # Expand folder by default
                folder_item.setExpanded(True)
                
                # Create folder in data manager
                self.data_manager.create_folder(category, current_path)
            
            current_parent = folder_item
        
        return current_parent
    
    def _on_tree_item_changed(self, item, column):
        """Handle tree item checkbox state change"""
        if column != 0:
            return
        
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return
        
        category = item_data.get("category")
        if not category:
            return
        
        try:
            if item_data.get("type") == "model":
                # Model checkbox changed
                url = item_data.get("url")
                checked = (item.checkState(0) == Qt.Checked)
                
                if url:
                    self._update_item_checked_state(category, url, checked)
                    
                    # Update parent folder tri-state
                    parent = item.parent()
                    if parent:
                        self._update_folder_tri_state(parent)
            
            elif item_data.get("type") == "folder":
                # Folder checkbox changed - update all children
                self._update_folder_children(item, item.checkState(0))
                
        except Exception as e:
            logging.error(f"Exception in _on_tree_item_changed: {e}", exc_info=True)
    
    def _update_folder_tri_state(self, folder_item):
        """Update folder tri-state based on children states"""
        if not folder_item:
            return
        
        total_children = 0
        checked_children = 0
        
        # Count model children (not folder children)
        for i in range(folder_item.childCount()):
            child = folder_item.child(i)
            child_data = child.data(0, Qt.UserRole)
            
            if child_data and child_data.get("type") == "model":
                total_children += 1
                if child.checkState(0) == Qt.Checked:
                    checked_children += 1
            elif child_data and child_data.get("type") == "folder":
                # For nested folders, count their checked state
                if child.checkState(0) == Qt.Checked:
                    checked_children += 1
                elif child.checkState(0) == Qt.PartiallyChecked:
                    checked_children += 0.5  # Partial counts as half
                total_children += 1
        
        # Set folder state based on children
        if total_children == 0:
            folder_item.setCheckState(0, Qt.Unchecked)
        elif checked_children == 0:
            folder_item.setCheckState(0, Qt.Unchecked)
        elif checked_children == total_children:
            folder_item.setCheckState(0, Qt.Checked)
        else:
            folder_item.setCheckState(0, Qt.PartiallyChecked)
        
        # Update parent folder if this is a subfolder
        parent = folder_item.parent()
        if parent and parent.data(0, Qt.UserRole) and parent.data(0, Qt.UserRole).get("type") == "folder":
            self._update_folder_tri_state(parent)
    
    def _update_folder_children(self, folder_item, state):
        """Update all children of a folder to match the folder's state"""
        if state == Qt.PartiallyChecked:
            return  # Don't change children for partial state
        
        checked = (state == Qt.Checked)
        
        # Update all children
        for i in range(folder_item.childCount()):
            child = folder_item.child(i)
            child_data = child.data(0, Qt.UserRole)
            
            if child_data and child_data.get("type") == "model":
                # Update model
                child.setCheckState(0, state)
                url = child_data.get("url")
                category = child_data.get("category")
                if url and category:
                    self._update_item_checked_state(category, url, checked)
            
            elif child_data and child_data.get("type") == "folder":
                # Recursively update subfolder
                child.setCheckState(0, state)
                self._update_folder_children(child, state)
    
    def _update_item_checked_state(self, key, url, checked):
        """Update the checked state of an item in the data"""
        success = self.data_manager.update_item_checked_state(key, url, checked)
        if success:
            self.data_changed.emit()
            self.data_manager.save_database()  # Auto-save when checkbox state changes
    
    def sync_ui_to_database(self):
        """Force synchronize all checkbox states from UI to database"""
        for key, tree_widget in self.tree_widgets.items():
            if key == 'max_parallel_downloads':
                continue
                
            # Recursively get all model items from tree
            self._sync_tree_items_to_database(tree_widget.invisibleRootItem(), key)
        
        # Save after all updates
        self.data_manager.save_database()
    
    def _sync_tree_items_to_database(self, parent_item, key):
        """Recursively sync tree items to database"""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            item_data = item.data(0, Qt.UserRole)
            
            if item_data and item_data.get("type") == "model":
                url = item_data.get("url")
                if url:
                    checked = (item.checkState(0) == Qt.Checked)
                    self.data_manager.update_item_checked_state(key, url, checked)
            elif item_data and item_data.get("type") == "folder":
                # Recursively process folder children
                self._sync_tree_items_to_database(item, key)
    
    def _set_all_checked(self, key, tree_widget, checked_state):
        """Set all items in a category to checked or unchecked"""
        # Update data
        self.data_manager.set_all_checked(key, checked_state)
        
        # Update UI - recursively set all items
        state = Qt.Checked if checked_state else Qt.Unchecked
        self._set_tree_items_checked(tree_widget.invisibleRootItem(), state)
        
        self.data_changed.emit()
        self.data_manager.save_database()  # Auto-save after bulk checkbox changes
    
    def _set_tree_items_checked(self, parent_item, state):
        """Recursively set all tree items to a specific checked state"""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            item.setCheckState(0, state)
            
            # Recursively set children
            if item.childCount() > 0:
                self._set_tree_items_checked(item, state)
    
    def _remove_items(self, key, tree_widget):
        """Remove selected items from the category"""
        selected_items = tree_widget.selectedItems()
        for item in selected_items:
            item_data = item.data(0, Qt.UserRole)
            if item_data and item_data.get("type") == "model":
                # Remove model
                url = item_data.get("url")
                if url:
                    self.data_manager.remove_item(key, url)
                
                # Remove from tree
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                    # Update parent folder tri-state
                    self._update_folder_tri_state(parent)
                else:
                    tree_widget.invisibleRootItem().removeChild(item)
            
            elif item_data and item_data.get("type") == "folder":
                # Remove folder and move all models to root
                folder_path = item_data.get("folder_path")
                if folder_path:
                    self.data_manager.delete_folder(key, folder_path)
                    
                    # Remove from tree (models will be moved to root in next refresh)
                    parent = item.parent()
                    if parent:
                        parent.removeChild(item)
                    else:
                        tree_widget.invisibleRootItem().removeChild(item)
        
        self.data_changed.emit()
        self.data_manager.save_database()  # Auto-save after removal
    
    def add_model_from_search(self, model_type, url):
        """Add a model URL from search results"""
        if model_type not in self.tree_widgets:
            return False
            
        tree_widget = self.tree_widgets[model_type]
        
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
                self._add_tree_item_with_checkbox(tree_widget, display_name, True, model_type, url, added_item.get('folder', ''), block_signals=False)
                self.data_changed.emit()
                self.data_manager.save_database()  # Auto-save after adding from search
                return True
        
        return False
    
    def refresh_ui_from_data(self):
        """Refresh all UI elements from the data"""
        # Update each category's tree widget
        for key in self.data_manager.data:
            if key != 'max_parallel_downloads' and key != 'folder_metadata' and key in self.tree_widgets:
                tree_widget = self.tree_widgets[key]
                tree_widget.clear()
                
                for item in self.data_manager.get_all_items(key):
                    # Use stored name if available, otherwise fetch or use URL
                    display_name = item.get('name') or item['url']
                    if not item.get('name'):
                        # Try to fetch name if not stored (for backward compatibility)
                        # Note: This could be slow, consider doing this asynchronously in the future
                        from data_manager import fetch_model_metadata
                        fetched_name = fetch_model_metadata(item['url'])
                        if fetched_name:
                            item['name'] = fetched_name
                            display_name = fetched_name
                    
                    self._add_tree_item_with_checkbox(
                        tree_widget,
                        display_name,
                        item.get('checked', True),
                        key,
                        item['url'],
                        item.get('folder', ''),
                        block_signals=True  # Block signals during UI refresh
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
            "clip_models": 16,
            "style_models": 17,
            "pulid_models": 18,
        }
    
    def _show_context_menu(self, category, tree_widget, position):
        """Show context menu for tree widget"""
        item = tree_widget.itemAt(position)
        menu = QMenu()
        
        if not item:
            # Right-click on empty space
            create_folder_action = menu.addAction("📁 Create New Folder")
            create_folder_action.triggered.connect(lambda: self._create_new_folder(category, tree_widget))
        else:
            item_data = item.data(0, Qt.UserRole)
            if item_data and item_data.get("type") == "folder":
                # Right-click on folder
                rename_action = menu.addAction("✏️ Rename Folder")
                rename_action.triggered.connect(lambda: self._rename_folder(category, tree_widget, item))
                
                delete_action = menu.addAction("🗑️ Delete Folder")
                delete_action.triggered.connect(lambda: self._delete_folder(category, tree_widget, item))
                
                menu.addSeparator()
                create_subfolder_action = menu.addAction("📁 Create Subfolder")
                create_subfolder_action.triggered.connect(lambda: self._create_subfolder(category, tree_widget, item))
                
            elif item_data and item_data.get("type") == "model":
                # Right-click on model
                move_to_folder_action = menu.addAction("📁 Move to Folder...")
                move_to_folder_action.triggered.connect(lambda: self._move_model_to_folder(category, tree_widget, item))
                
                move_to_root_action = menu.addAction("📤 Move to Root")
                move_to_root_action.triggered.connect(lambda: self._move_model_to_root(category, tree_widget, item))
        
        if not menu.isEmpty():
            menu.exec(tree_widget.mapToGlobal(position))
    
    def _create_new_folder(self, category, tree_widget):
        """Create a new folder at root level"""
        folder_name, ok = QInputDialog.getText(tree_widget, "Create Folder", "Folder name:")
        if ok and folder_name:
            # Check if folder already exists
            if self._folder_exists(tree_widget, folder_name):
                QMessageBox.warning(tree_widget, "Warning", f"Folder '{folder_name}' already exists.")
                return
            
            # Create folder in data manager
            self.data_manager.create_folder(category, folder_name)
            
            # Create folder in UI
            folder_item = QTreeWidgetItem(tree_widget)
            folder_item.setText(0, f"📁 {folder_name}")
            folder_item.setCheckState(0, Qt.Unchecked)
            folder_item.setFlags(folder_item.flags() | Qt.ItemIsUserCheckable)
            folder_item.setExpanded(True)
            
            # Store folder metadata
            folder_item.setData(0, Qt.UserRole, {
                "type": "folder",
                "folder_path": folder_name,
                "category": category
            })
            
            self.data_changed.emit()
            self.data_manager.save_database()
    
    def _create_subfolder(self, category, tree_widget, parent_folder_item):
        """Create a subfolder within an existing folder"""
        folder_name, ok = QInputDialog.getText(tree_widget, "Create Subfolder", "Subfolder name:")
        if ok and folder_name:
            parent_data = parent_folder_item.data(0, Qt.UserRole)
            parent_path = parent_data.get("folder_path", "")
            new_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
            
            # Check if subfolder already exists
            for i in range(parent_folder_item.childCount()):
                child = parent_folder_item.child(i)
                child_data = child.data(0, Qt.UserRole)
                if (child_data and child_data.get("type") == "folder" and 
                    child_data.get("folder_path") == new_path):
                    QMessageBox.warning(tree_widget, "Warning", f"Subfolder '{folder_name}' already exists.")
                    return
            
            # Create folder in data manager
            self.data_manager.create_folder(category, new_path)
            
            # Create folder in UI
            folder_item = QTreeWidgetItem(parent_folder_item)
            folder_item.setText(0, f"📁 {folder_name}")
            folder_item.setCheckState(0, Qt.Unchecked)
            folder_item.setFlags(folder_item.flags() | Qt.ItemIsUserCheckable)
            folder_item.setExpanded(True)
            
            # Store folder metadata
            folder_item.setData(0, Qt.UserRole, {
                "type": "folder",
                "folder_path": new_path,
                "category": category
            })
            
            self.data_changed.emit()
            self.data_manager.save_database()
    
    def _rename_folder(self, category, tree_widget, folder_item):
        """Rename an existing folder"""
        folder_data = folder_item.data(0, Qt.UserRole)
        old_path = folder_data.get("folder_path", "")
        old_name = old_path.split("/")[-1] if "/" in old_path else old_path
        
        new_name, ok = QInputDialog.getText(tree_widget, "Rename Folder", "New folder name:", text=old_name)
        if ok and new_name and new_name != old_name:
            # Calculate new path
            path_parts = old_path.split("/")[:-1] if "/" in old_path else []
            new_path = "/".join(path_parts + [new_name]) if path_parts else new_name
            
            # Rename in data manager
            if self.data_manager.rename_folder(category, old_path, new_path):
                # Update UI
                folder_item.setText(0, f"📁 {new_name}")
                folder_data["folder_path"] = new_path
                folder_item.setData(0, Qt.UserRole, folder_data)
                
                self.data_changed.emit()
                self.data_manager.save_database()
    
    def _delete_folder(self, category, tree_widget, folder_item):
        """Delete a folder and move models to root"""
        folder_data = folder_item.data(0, Qt.UserRole)
        folder_path = folder_data.get("folder_path", "")
        
        reply = QMessageBox.question(
            tree_widget, 
            "Delete Folder", 
            f"Delete folder '{folder_path}'?\nAll models will be moved to the root level.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Delete folder in data manager (moves models to root)
            self.data_manager.delete_folder(category, folder_path)
            
            # Remove from UI
            parent = folder_item.parent()
            if parent:
                parent.removeChild(folder_item)
            else:
                tree_widget.invisibleRootItem().removeChild(folder_item)
            
            # Refresh UI to show models moved to root
            self.refresh_ui_from_data()
            self.data_changed.emit()
            self.data_manager.save_database()
    
    def _move_model_to_folder(self, category, tree_widget, model_item):
        """Move a model to a selected folder"""
        # Get list of available folders
        folders = self._get_folder_list(tree_widget)
        if not folders:
            QMessageBox.information(tree_widget, "No Folders", "No folders available. Create a folder first.")
            return
        
        folder_path, ok = QInputDialog.getItem(tree_widget, "Move to Folder", "Select folder:", folders, 0, False)
        if ok and folder_path:
            model_data = model_item.data(0, Qt.UserRole)
            url = model_data.get("url")
            
            if url:
                # Block signals to prevent infinite loop during refresh
                tree_widget.blockSignals(True)
                
                # Update model folder in data manager
                self.data_manager.set_model_folder(category, url, folder_path)
                
                # Save changes
                self.data_changed.emit()
                self.data_manager.save_database()
                
                # Refresh UI to reflect changes
                self.refresh_ui_from_data()
                
                # Re-enable signals
                tree_widget.blockSignals(False)
    
    def _move_model_to_root(self, category, tree_widget, model_item):
        """Move a model to root level"""
        model_data = model_item.data(0, Qt.UserRole)
        url = model_data.get("url")
        
        if url:
            # Block signals to prevent infinite loop during refresh
            tree_widget.blockSignals(True)
            
            # Update model folder in data manager (empty string = root)
            self.data_manager.set_model_folder(category, url, "")
            
            # Save changes
            self.data_changed.emit()
            self.data_manager.save_database()
            
            # Refresh UI to reflect changes
            self.refresh_ui_from_data()
            
            # Re-enable signals
            tree_widget.blockSignals(False)
    
    def _folder_exists(self, tree_widget, folder_name):
        """Check if a folder with the given name exists at root level"""
        root = tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item_data = item.data(0, Qt.UserRole)
            if (item_data and item_data.get("type") == "folder" and 
                item_data.get("folder_path") == folder_name):
                return True
        return False
    
    def _get_folder_list(self, tree_widget):
        """Get list of all folder paths in the tree"""
        folders = []
        
        # If tree is empty or being refreshed, get folders from data manager
        category = None
        if tree_widget.topLevelItemCount() > 0:
            # Try to get category from any item
            item = tree_widget.topLevelItem(0)
            item_data = item.data(0, Qt.UserRole)
            if item_data:
                category = item_data.get("category")
        
        if not category:
            # Try to find category by matching tree widget
            for cat, tw in self.tree_widgets.items():
                if tw == tree_widget:
                    category = cat
                    break
        
        if category and "folder_metadata" in self.data_manager.data:
            # Get folders from data manager
            category_folders = self.data_manager.data.get("folder_metadata", {}).get(category, {})
            folders = list(category_folders.keys())
        else:
            # Fallback to tree traversal
            self._collect_folder_paths(tree_widget.invisibleRootItem(), folders)
            
        return folders
    
    def _collect_folder_paths(self, parent_item, folders):
        """Recursively collect folder paths"""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            item_data = item.data(0, Qt.UserRole)
            if item_data and item_data.get("type") == "folder":
                folder_path = item_data.get("folder_path")
                if folder_path and folder_path not in folders:
                    folders.append(folder_path)
                # Recursively check children
                self._collect_folder_paths(item, folders)
    
    
    # Backward compatibility property
    @property
    def list_widgets(self):
        """Backward compatibility property for list_widgets"""
        return self.tree_widgets