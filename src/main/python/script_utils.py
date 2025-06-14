#!/usr/bin/env python3
"""
Script Utilities Module

Handles script generation and parsing functionality.
"""

import re
from pathlib import Path
from data_manager import fetch_model_metadata


class ScriptGenerator:
    """Handles generation of provisioning scripts from data"""
    
    def __init__(self, template_file=None):
        if template_file:
            self.template_file = template_file
        else:
            # Try to find template in various locations
            possible_paths = [
                Path(__file__).parent / 'template.sh',
                Path(__file__).parent.parent / 'resources' / 'base' / 'template.sh',
                Path.cwd() / 'template.sh',
            ]
            
            for path in possible_paths:
                if path.exists():
                    self.template_file = str(path)
                    break
            else:
                # If running from fbs, try to get from resources
                try:
                    from fbs_runtime.application_context.PySide6 import ApplicationContext
                    ctx = ApplicationContext()
                    self.template_file = ctx.get_resource('template.sh')
                except:
                    self.template_file = 'template.sh'
    
    def generate_script(self, data):
        """Generate a script from the data"""
        # Load template from file
        try:
            with open(self.template_file, 'r') as f:
                template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template file '{self.template_file}' not found!")
        
        # Format the arrays - only include checked items with comments for model names
        def format_array(items):
            if not items:
                return ""
            # Filter to only checked items - ensure they are dicts and explicitly checked
            checked_items = []
            for item in items:
                if isinstance(item, dict) and item.get('checked', False):
                    checked_items.append(item)
            
            if not checked_items:
                return ""
            
            lines = []
            for item in checked_items:
                url = item.get('url', '')
                if not url:
                    continue
                name = item.get('name')
                if name and name != url:
                    # Add model name as comment
                    lines.append(f'    "{url}" # {name}')
                else:
                    lines.append(f'    "{url}"')
            return '\n'.join(lines)
        
        # Replace placeholders using string replacement
        replacements = {
            '{apt_packages}': format_array(data.get('apt_packages', [])),
            '{pip_packages}': format_array(data.get('pip_packages', [])),
            '{nodes}': format_array(data.get('nodes', [])),
            '{workflows}': format_array(data.get('workflows', [])),
            '{checkpoint_models}': format_array(data.get('checkpoint_models', [])),
            '{unet_models}': format_array(data.get('unet_models', [])),
            '{lora_models}': format_array(data.get('lora_models', [])),
            '{vae_models}': format_array(data.get('vae_models', [])),
            '{esrgan_models}': format_array(data.get('esrgan_models', [])),
            '{upscale_models}': format_array(data.get('upscale_models', [])),
            '{controlnet_models}': format_array(data.get('controlnet_models', [])),
            '{annotator_models}': format_array(data.get('annotator_models', [])),
            '{clip_vision_models}': format_array(data.get('clip_vision_models', [])),
            '{text_encoder_models}': format_array(data.get('text_encoder_models', [])),
            '{diffusion_models}': format_array(data.get('diffusion_models', [])),
            '{clip_models}': format_array(data.get('clip_models', [])),
            '{style_models}': format_array(data.get('style_models', [])),
            '{pulid_models}': format_array(data.get('pulid_models', [])),
            '{max_parallel_downloads}': str(data.get('max_parallel_downloads', 4))
        }
        
        # Apply replacements
        formatted_script = template
        for placeholder, value in replacements.items():
            formatted_script = formatted_script.replace(placeholder, value)
        
        return formatted_script


class ScriptParser:
    """Handles parsing of provisioning scripts"""
    
    def __init__(self):
        # Define patterns for each array
        self.patterns = {
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
            'diffusion_models': r'DIFFUSION_MODELS=\((.*?)\)',
            'clip_models': r'CLIP_MODELS=\((.*?)\)',
            'style_models': r'STYLE_MODELS=\((.*?)\)',
            'pulid_models': r'PULID_MODELS=\((.*?)\)'
        }
    
    def parse_script(self, content, data_manager):
        """
        Parse a bash script to extract arrays and settings - only updates check states
        
        Args:
            content: Script content to parse
            data_manager: DataManager instance to update
        """
        try:
            # Don't clear existing data - just uncheck everything first
            data_manager.clear_all_selections()
            
            # Extract items from each array and mark them as checked
            for key, pattern in self.patterns.items():
                try:
                    urls = self._extract_urls_from_array(content, pattern)
                    
                    for url, comment in urls:
                        try:
                            # Check if URL exists in database
                            existing_items = data_manager.get_all_items(key)
                            existing_item = None
                            
                            for item in existing_items:
                                if isinstance(item, dict) and item.get('url') == url:
                                    existing_item = item
                                    break
                            
                            if existing_item:
                                # Mark existing item as checked
                                success = data_manager.update_item_checked_state(key, url, True)
                                # Update name if we have a comment and no name stored
                                if comment and isinstance(existing_item, dict) and not existing_item.get('name'):
                                    # Update through data_manager method
                                    data_manager.update_item_name(key, url, comment)
                            else:
                                # Add new item to database
                                data_manager.add_item(key, url, checked=True)
                                # If we have a comment, update the name
                                if comment:
                                    data_manager.update_item_name(key, url, comment)
                                    
                        except Exception as e:
                            import logging
                            logging.error(f"Error processing URL {url} in category {key}: {e}")
                            raise
                            
                except Exception as e:
                    import logging
                    logging.error(f"Error extracting URLs for category {key}: {e}")
                    raise
            
            # Parse MAX_PARALLEL_DOWNLOADS setting
            max_parallel_match = re.search(r'MAX_PARALLEL_DOWNLOADS=(\d+)', content)
            if max_parallel_match:
                try:
                    max_parallel_value = int(max_parallel_match.group(1))
                    data_manager.update_max_parallel_downloads(max_parallel_value)
                except ValueError:
                    # If parsing fails, keep default value
                    pass
                    
        except Exception as e:
            import logging
            logging.error(f"Error in parse_script: {e}", exc_info=True)
            raise
    
    def _extract_urls_from_array(self, content, pattern):
        """Extract URLs and comments from a script array"""
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return []
        
        array_content = match.group(1)
        lines = array_content.strip().split('\n')
        urls = []
        
        for line in lines:
            line = line.strip()
            if line and line.startswith('"'):
                # Extract URL and optional comment
                url_match = re.match(r'"([^"]+)"(?:\s*#\s*(.*))?', line)
                if url_match:
                    url = url_match.group(1)
                    comment = url_match.group(2).strip() if url_match.group(2) else None
                    urls.append((url, comment))
        
        return urls