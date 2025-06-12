#!/usr/bin/env python3
"""
Data Management Module

Handles database operations, presets, and data persistence for the provisioning GUI.
"""

import json
import os
import re
import requests
import urllib.parse


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
    """Manages data storage, loading, and persistence"""
    
    def __init__(self, database_file='model_database.json', presets_file='presets.json'):
        self.database_file = database_file
        self.presets_file = presets_file
        self.data = self._get_default_data()
        self.presets = {}
    
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
    
    def load_database(self):
        """Load the database from JSON file"""
        try:
            if os.path.exists(self.database_file):
                with open(self.database_file, 'r') as f:
                    loaded_data = json.load(f)
                    
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
            with open(self.database_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving database: {e}")
    
    def load_presets(self):
        """Load presets from JSON file"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r') as f:
                    self.presets = json.load(f)
        except Exception as e:
            print(f"Error loading presets: {e}")
        return self.presets
    
    def save_presets(self):
        """Save presets to JSON file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.presets, f, indent=2)
        except Exception as e:
            print(f"Error saving presets: {e}")
    
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
            
        for item in self.data[category]:
            if item['url'] == url:
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
    
    def create_preset(self, name, overwrite=False):
        """Create a preset from current checked items"""
        if name in self.presets and not overwrite:
            return False
            
        # Save only checked items
        preset_data = {}
        for key in self.data:
            if key == 'max_parallel_downloads':
                preset_data[key] = self.data[key]
            else:
                # Only save checked items
                preset_data[key] = [item['url'] for item in self.data[key] if item.get('checked', True)]
        
        self.presets[name] = preset_data
        return True
    
    def load_preset(self, name):
        """Load a preset configuration"""
        if name not in self.presets:
            return False
            
        preset_data = self.presets[name]
        
        # First, uncheck all items in the database
        for key in self.data:
            if key == 'max_parallel_downloads':
                self.data[key] = preset_data.get(key, 4)
            else:
                for item in self.data[key]:
                    item['checked'] = False
        
        # Then check items that are in the preset
        for key, urls in preset_data.items():
            if key != 'max_parallel_downloads' and isinstance(urls, list):
                for url in urls:
                    # Find existing item in database
                    existing_item = None
                    for item in self.data[key]:
                        if item['url'] == url:
                            existing_item = item
                            break
                    
                    if existing_item:
                        # Mark existing item as checked
                        existing_item['checked'] = True
                    else:
                        # Add new item to database if it doesn't exist
                        model_name = fetch_model_metadata(url)
                        self.data[key].append({
                            'url': url,
                            'checked': True,
                            'name': model_name
                        })
        
        return True
    
    def delete_preset(self, name):
        """Delete a preset"""
        if name in self.presets:
            del self.presets[name]
            return True
        return False