#!/usr/bin/env python3
"""
Data Management Module

Handles database operations and data persistence for the provisioning GUI.
Now integrated with GitHub repository for presets storage.
"""

import json
import os
import re
import requests
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def fetch_model_metadata(url):
    """Fetch model metadata from URL to get the model name"""
    try:
        # CivitAI API URL pattern
        if 'civitai.com/api/download/models/' in url:
            # Extract model version ID from URL
            match = re.search(r'/models/(\d+)', url)
            if match:
                model_version_id = match.group(1)
                api_url = f"https://civitai.com/api/v1/model-versions/{model_version_id}"
                
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    model_name = data.get('model', {}).get('name', 'Unknown Model')
                    version_name = data.get('name', '')
                    creator = data.get('model', {}).get('creator', {}).get('username', 'Unknown')
                    
                    # Format: "🎨 Model Name (Version) by Creator"
                    full_name = f"🎨 {model_name}"
                    if version_name and version_name.lower() != model_name.lower():
                        full_name += f" ({version_name})"
                    full_name += f" by {creator}"
                    
                    return full_name
        
        # CivitAI direct URL pattern
        elif 'civitai.com' in url and '/models/' in url:
            return f"🎨 {_extract_filename_from_url(url)}"
        
        # Hugging Face URL pattern
        elif 'huggingface.co' in url:
            # Extract model repo from URL
            match = re.search(r'huggingface\.co/([^/]+/[^/]+)', url)
            if match:
                repo_id = match.group(1)
                
                # Extract filename from URL if present - expanded patterns
                filename_match = re.search(r'/([^/]+\.(safetensors|ckpt|pt|bin|pth|json|yaml|yml))(?:\?|$)', url)
                if filename_match:
                    filename = filename_match.group(1)
                    # For specific filenames, use the filename as the main identifier
                    return f"🤗 {filename}"
                else:
                    # For general repo access, use repo name
                    return f"🤗 {repo_id}"
        
        # GitHub URL pattern for nodes
        elif 'github.com' in url:
            match = re.search(r'github\.com/([^/]+/[^/]+)', url)
            if match:
                repo_name = match.group(1)
                return f"📁 {repo_name}"
        
        # Google Drive pattern
        elif 'drive.google.com' in url or 'googleapis.com' in url:
            filename = _extract_filename_from_url(url)
            return f"💾 {filename}" if filename else "💾 Google Drive File"
        
        # OneDrive/SharePoint pattern
        elif 'onedrive.live.com' in url or 'sharepoint.com' in url or '1drv.ms' in url:
            filename = _extract_filename_from_url(url)
            return f"☁️ {filename}" if filename else "☁️ OneDrive File"
        
        # Dropbox pattern
        elif 'dropbox.com' in url:
            filename = _extract_filename_from_url(url)
            return f"📦 {filename}" if filename else "📦 Dropbox File"
        
        # Direct file URLs (many annotator models)
        elif any(ext in url.lower() for ext in ['.pth', '.onnx', '.pkl', '.bin', '.safetensors', '.pt']):
            filename = _extract_filename_from_url(url)
            # Try to determine platform from domain
            if 'huggingface.co' in url:
                return f"🤗 {filename}"
            elif 'github.com' in url or 'githubusercontent.com' in url:
                return f"📁 {filename}"
            else:
                return f"🔗 {filename}"
        
        # Fallback: try to extract filename from URL
        filename = _extract_filename_from_url(url)
        if filename:
            return f"🔗 {filename}"
            
    except Exception as e:
        print(f"Error fetching metadata for {url}: {e}")
    
    return None


def _extract_filename_from_url(url):
    """Extract filename from URL, handling various URL patterns"""
    try:
        # Remove query parameters and fragments
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        
        # Handle special cases
        if 'drive.google.com' in url:
            # Try to extract filename from query params
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'filename' in query_params:
                return query_params['filename'][0]
        
        # Get the last part of the path
        filename = path.split('/')[-1]
        
        # If filename has an extension, return it
        if filename and '.' in filename:
            return filename
        
        # Try to get from second to last part if last part is empty or looks like an ID
        path_parts = [p for p in path.split('/') if p]
        if len(path_parts) >= 2:
            potential_filename = path_parts[-2]
            if '.' in potential_filename:
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
    
    def set_github_integration(self, github_integration):
        """Set the GitHub integration instance"""
        self.github_integration = github_integration
        # Database always stays local - never in the repository
    
    def load_database(self):
        """Load the database from JSON file"""
        try:
            loaded_data = None
            
            # Load from the single database location
            if self.database_file and self.database_file.exists():
                with open(self.database_file, 'r') as f:
                    loaded_data = json.load(f)
            
            if loaded_data:
                # Merge with existing data structure
                for key in self.data:
                    if key in loaded_data:
                        if key == 'max_parallel_downloads':
                            self.data[key] = loaded_data[key]
                        else:
                            # Ensure all items have the new format
                            items = loaded_data[key]
                            if items and isinstance(items[0], str):
                                # Old format - convert to new with name fetching
                                self.data[key] = [{'url': url, 'checked': True, 'name': None} for url in items]
                            else:
                                # New format - ensure name field exists
                                converted_items = []
                                for item in items:
                                    if isinstance(item, dict):
                                        # Add name field if missing
                                        if 'name' not in item:
                                            item['name'] = None
                                        converted_items.append(item)
                                    else:
                                        # Legacy string format
                                        converted_items.append({'url': item, 'checked': True, 'name': None})
                                self.data[key] = converted_items
                
                
        except Exception as e:
            print(f"Error loading database: {e}")
    
    def save_database(self):
        """Save the entire database to a JSON file"""
        try:
            # Ensure parent directory exists
            self.database_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.database_file, 'w') as f:
                json.dump(self.data, f, indent=2)
                    
        except Exception as e:
            print(f"Error saving database: {e}")
    
    
    def add_item(self, category, url, checked=True):
        """Add an item to a category"""
        if category not in self.data or category == 'max_parallel_downloads':
            return False
            
        # Check if item already exists
        if any(item['url'] == url for item in self.data[category]):
            return False
            
        # Fetch model name for display
        model_name = fetch_model_metadata(url)
        
        # Add to data with checked state and name
        item_data = {
            'url': url,
            'checked': checked,
            'name': model_name
        }
        self.data[category].append(item_data)
        return True
    
    def remove_item(self, category, url):
        """Remove an item from a category"""
        if category not in self.data or category == 'max_parallel_downloads':
            return False
            
        self.data[category] = [item for item in self.data[category] if item['url'] != url]
        return True
    
    def update_item_checked_state(self, category, url, checked):
        """Update the checked state of an item"""
        if category not in self.data or category == 'max_parallel_downloads':
            return False
        
        
        for i, item in enumerate(self.data[category]):
            if item['url'] == url:
                old_state = item.get('checked', True)
                item['checked'] = checked
                return True
        
        return False
    
    def set_all_checked(self, category, checked_state):
        """Set all items in a category to checked or unchecked"""
        if category not in self.data or category == 'max_parallel_downloads':
            return False
            
        for item in self.data[category]:
            item['checked'] = checked_state
        return True
    
    def clear_all_selections(self):
        """Uncheck all models in the database"""
        for key in self.data:
            if key != 'max_parallel_downloads':
                for item in self.data[key]:
                    item['checked'] = False
    
    def get_checked_items(self, category):
        """Get all checked items for a category"""
        if category not in self.data or category == 'max_parallel_downloads':
            return []
        return [item for item in self.data[category] if item.get('checked', True)]
    
    def get_all_items(self, category):
        """Get all items for a category"""
        if category not in self.data or category == 'max_parallel_downloads':
            return []
        return self.data[category]
    
    def update_max_parallel_downloads(self, value):
        """Update the max parallel downloads setting"""
        try:
            self.data['max_parallel_downloads'] = int(value)
            return True
        except (ValueError, TypeError):
            return False
    
    
    def refresh_all_model_names(self, progress_callback=None):
        """Refresh all model names from their sources"""
        total_items = 0
        refreshed = 0
        
        # Count total items
        for key in self.data:
            if key != 'max_parallel_downloads':
                total_items += len(self.data[key])
        
        # Refresh each category
        for key in self.data:
            if key == 'max_parallel_downloads':
                continue
                
            for item in self.data[key]:
                # Always try to refresh if:
                # 1. No name exists
                # 2. Name is same as URL
                # 3. Name contains platform emoji (indicating it was auto-fetched)
                should_refresh = (
                    not item.get('name') or 
                    item['name'] == item['url'] or
                    any(emoji in item.get('name', '') for emoji in ['🎨', '🤗', '📁', '💾', '☁️', '📦', '🔗'])
                )
                
                if should_refresh:
                    # Fetch new name
                    new_name = fetch_model_metadata(item['url'])
                    if new_name and new_name != item['url']:
                        item['name'] = new_name
                    
                refreshed += 1
                if progress_callback:
                    progress_callback(refreshed, total_items)
        
        # Save the updated database
        self.save_database()
        return refreshed, total_items
    
    def list_available_presets(self) -> List[str]:
        """List all available presets from GitHub repository"""
        if not self.github_integration:
            return []
        return self.github_integration.list_presets()
    
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
            with open(preset_path, 'r') as f:
                content = f.read()
            
            parsed_data = parser.parse_script(content)
            
            # Update selections based on preset (don't replace database)
            # First clear all selections
            self.clear_all_selections()
            
            # Then check items that are in the preset
            for category, urls in parsed_data.items():
                if category in self.data and category != 'max_parallel_downloads':
                    for url in urls:
                        # Find and check the item
                        for item in self.data[category]:
                            if item['url'] == url:
                                item['checked'] = True
                                break
                        else:
                            # URL not in database, add it
                            self.add_item(category, url, checked=True)
                elif category == 'max_parallel_downloads':
                    self.data['max_parallel_downloads'] = urls
            
            # Save the updated database
            self.save_database()
            return True, f"Loaded preset: {preset_name}"
            
        except Exception as e:
            return False, f"Error loading preset: {str(e)}"
    
    def save_preset_to_repo(self, preset_name: str, commit_message: str = None) -> Tuple[bool, str]:
        """Save current selections as a preset to the GitHub repository"""
        if not self.github_integration:
            return False, "GitHub integration not configured"
        
        try:
            # Import script generator
            from script_utils import ScriptGenerator
            generator = ScriptGenerator()
            
            # Generate script content from current selections
            script_content = generator.generate_script(self.data)
            
            # Save to repository
            success, message = self.github_integration.save_preset(preset_name, script_content)
            if not success:
                return False, message
            
            # Commit and push if requested
            if commit_message:
                success, message = self.github_integration.commit_and_push(
                    commit_message, 
                    [preset_name]
                )
                if not success:
                    return False, f"Preset saved locally but push failed: {message}"
            
            return True, f"Preset saved: {preset_name}"
            
        except Exception as e:
            return False, f"Error saving preset: {str(e)}"