#!/usr/bin/env python3
"""
Data Management Module

Handles database operations and data persistence for the provisioning GUI.
Now integrated with GitHub repository for presets storage.
"""

import json
import logging
import re
import urllib.parse
from pathlib import Path
from typing import List, Tuple

import requests


def fetch_model_metadata(url):
    """Fetch model metadata from URL to get the model name"""
    try:
        # CivitAI API URL pattern
        if "civitai.com/api/download/models/" in url:
            # Extract model version ID from URL
            match = re.search(r"/models/(\d+)", url)
            if match:
                model_version_id = match.group(1)
                api_url = (
                    f"https://civitai.com/api/v1/model-versions/{model_version_id}"
                )

                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    model_name = data.get("model", {}).get("name", "Unknown Model")
                    version_name = data.get("name", "")
                    creator = (
                        data.get("model", {})
                        .get("creator", {})
                        .get("username", "Unknown")
                    )

                    # Format: "🎨 Model Name (Version) by Creator"
                    full_name = f"🎨 {model_name}"
                    if version_name and version_name.lower() != model_name.lower():
                        full_name += f" ({version_name})"
                    full_name += f" by {creator}"

                    return full_name

        # CivitAI direct URL pattern
        elif "civitai.com" in url and "/models/" in url:
            return f"🎨 {_extract_filename_from_url(url)}"

        # Hugging Face URL pattern
        elif "huggingface.co" in url:
            # Extract model repo from URL
            match = re.search(r"huggingface\.co/([^/]+/[^/]+)", url)
            if match:
                repo_id = match.group(1)

                # Extract filename from URL if present - expanded patterns
                filename_match = re.search(
                    r"/([^/]+\.(safetensors|ckpt|pt|bin|pth|json|yaml|yml))(?:\?|$)",
                    url,
                )
                if filename_match:
                    filename = filename_match.group(1)
                    # For specific filenames, use the filename as the main identifier
                    return f"🤗 {filename}"
                else:
                    # For general repo access, use repo name
                    return f"🤗 {repo_id}"

        # GitHub URL pattern for nodes
        elif "github.com" in url:
            match = re.search(r"github\.com/([^/]+/[^/]+)", url)
            if match:
                repo_name = match.group(1)
                return f"📁 {repo_name}"

        # Google Drive pattern
        elif "drive.google.com" in url or "googleapis.com" in url:
            filename = _extract_filename_from_url(url)
            return f"💾 {filename}" if filename else "💾 Google Drive File"

        # OneDrive/SharePoint pattern
        elif "onedrive.live.com" in url or "sharepoint.com" in url or "1drv.ms" in url:
            filename = _extract_filename_from_url(url)
            return f"☁️ {filename}" if filename else "☁️ OneDrive File"

        # Dropbox pattern
        elif "dropbox.com" in url:
            filename = _extract_filename_from_url(url)
            return f"📦 {filename}" if filename else "📦 Dropbox File"

        # Direct file URLs (many annotator models)
        elif any(
            ext in url.lower()
            for ext in [".pth", ".onnx", ".pkl", ".bin", ".safetensors", ".pt"]
        ):
            filename = _extract_filename_from_url(url)
            # Try to determine platform from domain
            if "huggingface.co" in url:
                return f"🤗 {filename}"
            elif "github.com" in url or "githubusercontent.com" in url:
                return f"📁 {filename}"
            else:
                return f"🔗 {filename}"

        # Fallback: try to extract filename from URL
        filename = _extract_filename_from_url(url)
        if filename:
            return f"🔗 {filename}"

    except Exception as e:
        logging.debug(f"Error fetching metadata for {url}: {e}")

    return None


def _extract_filename_from_url(url):
    """Extract filename from URL, handling various URL patterns"""
    try:
        # Remove query parameters and fragments
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path

        # Handle special cases
        if "drive.google.com" in url:
            # Try to extract filename from query params
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if "filename" in query_params:
                return query_params["filename"][0]

        # Get the last part of the path
        filename = path.split("/")[-1]

        # If filename has an extension, return it
        if filename and "." in filename:
            return filename

        # Try to get from second to last part if last part is empty or looks like an ID
        path_parts = [p for p in path.split("/") if p]
        if len(path_parts) >= 2:
            potential_filename = path_parts[-2]
            if "." in potential_filename:
                return potential_filename

        # If no good filename found, return the last non-empty path component
        if path_parts:
            return path_parts[-1]

    except Exception:
        pass

    return None


class DataManager:
    """Manages data storage, loading, and persistence with GitHub repository integration"""

    def __init__(self, app_data_dir=None):
        # Use app data directory for database
        if app_data_dir:
            self.app_data_dir = Path(app_data_dir)
        else:
            self.app_data_dir = Path.home() / ".vastai-provisioning"

        self.app_data_dir.mkdir(exist_ok=True)
        # Single database location - always in the presets repository when configured
        self.database_file = self.app_data_dir / "model_database.json"
        self.data = self._get_default_data()
        self.github_integration = None

    def _get_default_data(self):
        """Get the default data structure"""
        return {
            "apt_packages": [],
            "pip_packages": [],
            "nodes": [],
            "workflows": [],
            "checkpoint_models": [],
            "unet_models": [],
            "lora_models": [],
            "vae_models": [],
            "esrgan_models": [],
            "upscale_models": [],
            "controlnet_models": [],
            "annotator_models": [],
            "clip_vision_models": [],
            "text_encoder_models": [],
            "diffusion_models": [],
            "clip_models": [],
            "style_models": [],
            "pulid_models": [],
            "max_parallel_downloads": 4,
            "folder_metadata": {},
        }

    def set_github_integration(self, github_integration):
        """Set the GitHub integration instance"""
        self.github_integration = github_integration
        # Database always stays local - never in the repository

    def _validate_and_fix_data(self):
        """Validate and fix data structure to ensure all items are in correct format"""
        for key in self.data:
            if key in ["max_parallel_downloads", "folder_metadata"]:
                continue
                
            if not isinstance(self.data[key], list):
                # If it's not a list, make it an empty list
                self.data[key] = []
                continue
                
            # Fix any string items to be proper dictionaries
            fixed_items = []
            for i, item in enumerate(self.data[key]):
                if isinstance(item, str):
                    # Convert string to proper format
                    fixed_items.append({
                        "url": item,
                        "checked": True,
                        "name": None,
                        "folder": ""
                    })
                elif isinstance(item, dict):
                    # Ensure all required fields exist
                    if "url" not in item:
                        continue  # Skip invalid items
                    if "checked" not in item:
                        item["checked"] = True
                    if "name" not in item:
                        item["name"] = None
                    if "folder" not in item:
                        item["folder"] = ""
                    fixed_items.append(item)
            
            self.data[key] = fixed_items

    def load_database(self):
        """Load the database from JSON file"""
        try:
            loaded_data = None

            # Load from the single database location
            if self.database_file and self.database_file.exists():
                with open(self.database_file, "r") as f:
                    loaded_data = json.load(f)

            if loaded_data:
                # Merge with existing data structure
                for key in self.data:
                    if key in loaded_data:
                        if key == "max_parallel_downloads":
                            self.data[key] = loaded_data[key]
                        elif key == "folder_metadata":
                            # Handle folder metadata specially - it should be a dict
                            if isinstance(loaded_data[key], dict):
                                self.data[key] = loaded_data[key]
                            else:
                                # If it's not a dict (corrupted), reset it
                                self.data[key] = {}
                        else:
                            # Skip if the key shouldn't be a list (only process expected model categories)
                            if not isinstance(self.data[key], list):
                                continue
                            
                            # Ensure all items have the new format
                            items = loaded_data[key]
                            if not isinstance(items, list):
                                # Skip non-list items for model categories
                                continue
                                
                            if items and len(items) > 0 and isinstance(items[0], str):
                                # Old format - convert to new with name fetching and folder support
                                self.data[key] = [
                                    {"url": url, "checked": True, "name": None, "folder": ""}
                                    for url in items
                                ]
                            else:
                                # New format - ensure name and folder fields exist
                                converted_items = []
                                for item in items:
                                    if isinstance(item, dict):
                                        # Create a new dict to avoid modifying the original
                                        new_item = item.copy()
                                        # Add name field if missing
                                        if "name" not in new_item:
                                            new_item["name"] = None
                                        # Add folder field if missing (for folder support)
                                        if "folder" not in new_item:
                                            new_item["folder"] = ""
                                        converted_items.append(new_item)
                                    elif isinstance(item, str):
                                        # Legacy string format
                                        converted_items.append(
                                            {"url": item, "checked": True, "name": None, "folder": ""}
                                        )
                                    else:
                                        # Skip any other types
                                        pass
                                self.data[key] = converted_items
            
            # Validate and fix data after loading
            self._validate_and_fix_data()

        except Exception as e:
            logging.error(f"Error loading database: {e}")
            # Even on error, validate the data structure
            self._validate_and_fix_data()

    def save_database(self):
        """Save the entire database to a JSON file"""
        try:
            # Validate data before saving
            self._validate_and_fix_data()
            
            # Ensure parent directory exists
            self.database_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.database_file, "w") as f:
                json.dump(self.data, f, indent=2)

        except Exception as e:
            logging.error(f"Error saving database: {e}")

    def add_item(self, category, url, checked=True):
        """Add an item to a category"""
        if category not in self.data or category == "max_parallel_downloads":
            return False

        # Check if item already exists
        if any(isinstance(item, dict) and item.get("url") == url for item in self.data[category]):
            return False

        # Fetch model name for display
        model_name = fetch_model_metadata(url)

        # Add to data with checked state, name, and empty folder
        item_data = {"url": url, "checked": checked, "name": model_name, "folder": ""}
        self.data[category].append(item_data)
        return True

    def remove_item(self, category, url):
        """Remove an item from a category"""
        if category not in self.data or category == "max_parallel_downloads":
            return False

        self.data[category] = [
            item for item in self.data[category] 
            if isinstance(item, dict) and item.get("url") != url
        ]
        return True

    def update_item_checked_state(self, category, url, checked):
        """Update the checked state of an item"""
        if category not in self.data or category == "max_parallel_downloads":
            return False

        for item in self.data[category]:
            if isinstance(item, dict) and item.get("url") == url:
                item["checked"] = checked
                return True

        return False
    
    def update_item_name(self, category, url, name):
        """Update the name of an item"""
        if category not in self.data or category == "max_parallel_downloads":
            return False

        for item in self.data[category]:
            if isinstance(item, dict) and item.get("url") == url:
                item["name"] = name
                return True

        return False

    def set_all_checked(self, category, checked_state):
        """Set all items in a category to checked or unchecked"""
        if category not in self.data or category == "max_parallel_downloads":
            return False

        for item in self.data[category]:
            if isinstance(item, dict):
                item["checked"] = checked_state
        return True

    def clear_all_selections(self):
        """Uncheck all models in the database"""
        for key in self.data:
            if key != "max_parallel_downloads" and isinstance(self.data[key], list):
                for item in self.data[key]:
                    if isinstance(item, dict):
                        item["checked"] = False

    def get_checked_items(self, category):
        """Get all checked items for a category"""
        if category not in self.data or category == "max_parallel_downloads":
            return []
        return [item for item in self.data[category] if item.get("checked", True)]

    def get_all_items(self, category):
        """Get all items for a category"""
        if category not in self.data or category == "max_parallel_downloads":
            return []
        return self.data[category]

    def update_max_parallel_downloads(self, value):
        """Update the max parallel downloads setting"""
        try:
            self.data["max_parallel_downloads"] = int(value)
            return True
        except (ValueError, TypeError):
            return False

    def refresh_all_model_names(self, progress_callback=None):
        """Refresh all model names from their sources"""
        total_items = 0
        refreshed = 0

        # Count total items
        for key in self.data:
            if key != "max_parallel_downloads":
                total_items += len(self.data[key])

        # Refresh each category
        for key in self.data:
            if key == "max_parallel_downloads":
                continue

            for item in self.data[key]:
                # Always try to refresh if:
                # 1. No name exists
                # 2. Name is same as URL
                # 3. Name contains platform emoji (indicating it was auto-fetched)
                should_refresh = (
                    not item.get("name")
                    or item["name"] == item["url"]
                    or any(
                        emoji in item.get("name", "")
                        for emoji in ["🎨", "🤗", "📁", "💾", "☁️", "📦", "🔗"]
                    )
                )

                if should_refresh:
                    # Fetch new name
                    new_name = fetch_model_metadata(item["url"])
                    if new_name and new_name != item["url"]:
                        item["name"] = new_name

                refreshed += 1
                if progress_callback:
                    progress_callback(refreshed, total_items)

        # Save the updated database
        self.save_database()
        return refreshed, total_items

    def list_available_presets(self) -> List[str]:
        """List only actual preset files from GitHub repository (excluding system files)"""
        # Only return presets if GitHub integration is properly configured AND repo exists
        if (
            not self.github_integration
            or not self.github_integration.local_path
            or not self.github_integration.local_path.exists()
        ):
            return []

        all_files = self.github_integration.list_presets()

        # Only return actual preset files, exclude system/template files
        excluded_files = {
            "default.sh",
            "provisioning.sh",
            "template.sh",
            "nocheck.sh",
            "install.sh",
            "setup.sh",
        }

        presets = []
        for file_path in all_files:
            filename = Path(file_path).name
            if filename.lower() not in excluded_files:
                presets.append(file_path)

        return presets

    def load_preset_from_repo(self, preset_name: str) -> Tuple[bool, str]:
        """Load a preset from the GitHub repository"""
        if not self.github_integration:
            return False, "GitHub integration not configured"

        preset_path = self.github_integration.get_preset_path(preset_name)
        if not preset_path:
            return False, f"Preset not found: {preset_name}"

        try:
            # Import script parser
            from script_utils import ScriptParser

            parser = ScriptParser()

            # Parse the preset file
            with open(preset_path, "r") as f:
                content = f.read()

            # Parse the script directly with the data manager
            parser.parse_script(content, self)

            # Save the updated database
            self.save_database()
            return True, f"Loaded preset: {preset_name}"

        except Exception as e:
            import traceback
            logging.error(f"Error loading preset: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return False, f"Error loading preset: {str(e)}"

    def save_preset_to_repo(
        self, preset_name: str, commit_message: str = None
    ) -> Tuple[bool, str]:
        """Save current selections as a preset to the GitHub repository"""
        if not self.github_integration:
            return False, "GitHub integration not configured"

        try:
            # Import script generator
            from script_utils import ScriptGenerator

            generator = ScriptGenerator()

            # Ensure database is saved before generating script
            self.save_database()
            
            # Generate script content from current selections
            script_content = generator.generate_script(self.data)

            # Save to repository
            success, message = self.github_integration.save_preset(
                preset_name, script_content
            )
            if not success:
                return False, message

            # Commit and push if requested
            if commit_message:
                success, message = self.github_integration.commit_and_push(
                    commit_message, [preset_name]
                )
                if not success:
                    return False, f"Preset saved locally but push failed: {message}"

            return True, f"Preset saved: {preset_name}"

        except Exception as e:
            return False, f"Error saving preset: {str(e)}"

    # Folder management methods
    def set_model_folder(self, category: str, url: str, folder_path: str):
        """Set the folder path for a specific model"""
        if category not in self.data or not isinstance(self.data[category], list):
            return False
        
        for item in self.data[category]:
            if item["url"] == url:
                item["folder"] = folder_path
                return True
        return False

    def get_models_in_folder(self, category: str, folder_path: str = ""):
        """Get all models in a specific folder (empty string = root level)"""
        if category not in self.data or not isinstance(self.data[category], list):
            return []
        
        return [item for item in self.data[category] if item.get("folder", "") == folder_path]

    def get_folder_structure(self, category: str):
        """Get the hierarchical folder structure for a category"""
        if category not in self.data or not isinstance(self.data[category], list):
            return {}
        
        structure = {}
        
        for item in self.data[category]:
            folder_path = item.get("folder", "")
            
            if not folder_path:
                # Root level item
                if "_root" not in structure:
                    structure["_root"] = []
                structure["_root"].append(item)
            else:
                # Create nested structure
                parts = folder_path.split("/")
                current = structure
                
                for part in parts:
                    if part not in current:
                        current[part] = {"_items": [], "_folders": {}}
                    current = current[part]["_folders"]
                
                # Add item to the final folder
                folder_key = "/".join(parts)
                if folder_key not in structure:
                    structure[folder_key] = {"_items": [], "_folders": {}}
                structure[folder_key]["_items"].append(item)
        
        return structure

    def create_folder(self, category: str, folder_path: str):
        """Create folder metadata entry"""
        # Check if category exists and is a list (model category)
        if category not in self.data or not isinstance(self.data[category], list):
            return False
        
        if "folder_metadata" not in self.data:
            self.data["folder_metadata"] = {}
        
        if category not in self.data["folder_metadata"]:
            self.data["folder_metadata"][category] = {}
        
        self.data["folder_metadata"][category][folder_path] = {
            "expanded": True,
            "custom_icon": None,
            "description": ""
        }
        return True

    def delete_folder(self, category: str, folder_path: str):
        """Delete a folder and move all its models to root level"""
        if category not in self.data or not isinstance(self.data[category], list):
            return False
        
        # Move all models in this folder to root
        for item in self.data[category]:
            if item.get("folder", "").startswith(folder_path):
                item["folder"] = ""
        
        # Remove folder metadata
        if ("folder_metadata" in self.data and 
            category in self.data["folder_metadata"] and 
            folder_path in self.data["folder_metadata"][category]):
            del self.data["folder_metadata"][category][folder_path]
        
        return True

    def rename_folder(self, category: str, old_path: str, new_path: str):
        """Rename a folder and update all model paths"""
        if category not in self.data or not isinstance(self.data[category], list):
            return False
        
        # Update all models in this folder
        for item in self.data[category]:
            folder = item.get("folder", "")
            if folder == old_path:
                item["folder"] = new_path
            elif folder.startswith(old_path + "/"):
                # Update subfolder paths
                item["folder"] = new_path + folder[len(old_path):]
        
        # Update folder metadata
        if ("folder_metadata" in self.data and 
            category in self.data["folder_metadata"] and 
            old_path in self.data["folder_metadata"][category]):
            metadata = self.data["folder_metadata"][category][old_path]
            del self.data["folder_metadata"][category][old_path]
            self.data["folder_metadata"][category][new_path] = metadata
        
        return True

    def get_folder_metadata(self, category: str, folder_path: str):
        """Get metadata for a specific folder"""
        if ("folder_metadata" not in self.data or 
            category not in self.data["folder_metadata"] or 
            folder_path not in self.data["folder_metadata"][category]):
            return {"expanded": True, "custom_icon": None, "description": ""}
        
        return self.data["folder_metadata"][category][folder_path]

    def set_folder_metadata(self, category: str, folder_path: str, metadata: dict):
        """Set metadata for a specific folder"""
        if "folder_metadata" not in self.data:
            self.data["folder_metadata"] = {}
        
        if category not in self.data["folder_metadata"]:
            self.data["folder_metadata"][category] = {}
        
        self.data["folder_metadata"][category][folder_path] = metadata
        return True
