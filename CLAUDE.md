# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains provisioning templates for Vast.ai GPU instances, specifically designed for setting up ComfyUI environments. The main script `default.sh` handles automated installation of packages, ComfyUI nodes, and AI models.

## Architecture

The provisioning system is built around a single bash script that:
- Activates a Python virtual environment at `/venv/main`
- Downloads and installs ComfyUI custom nodes from GitHub
- Downloads AI models from Hugging Face and CivitAI
- Manages authentication tokens for model downloads
- Provides arrays for easy configuration of:
  - APT packages
  - Python packages
  - ComfyUI nodes
  - AI models (checkpoints, LoRA, VAE, ControlNet, etc.)

## Key Patterns

1. **Model Organization**: Models are downloaded to specific ComfyUI subdirectories based on type (checkpoints, unet, lora, controlnet, vae, esrgan)
2. **Token Authentication**: Supports both `HF_TOKEN` for Hugging Face and `CIVITAI_TOKEN` for CivitAI downloads
3. **Auto-update**: Nodes can be automatically updated if `AUTO_UPDATE` is not set to "false"
4. **Provisioning Control**: Users can disable provisioning by creating `/.noprovisioning` file

## Usage

To use this template:
1. Uncomment and add desired items to the configuration arrays at the top of `default.sh`
2. Add model URLs to the appropriate model arrays
3. Set environment variables `HF_TOKEN` and/or `CIVITAI_TOKEN` if downloading from authenticated sources
4. The script will run automatically on container start unless disabled

## GUI Tool

A GUI application (`provisioning_gui.py`) provides an advanced interface for managing provisioning scripts with smart model identification and a persistent global database. The application uses a modular architecture with the following components:

### Architecture
- **`provisioning_gui.py`** - Main GUI orchestrator and user interface
- **`model_search.py`** - CivitAI and Hugging Face model search functionality  
- **`data_manager.py`** - Database persistence and data operations
- **`script_utils.py`** - Script generation and parsing utilities
- **`category_panels.py`** - UI panel management and interactions

### Status: ✅ Enhanced with Smart Features
- **Smart Model Names**: Automatically fetches model metadata from CivitAI and Hugging Face
- **Global Database**: Persistent model database that grows over time
- **Platform Indicators**: Visual emojis to identify model sources (🎨 CivitAI, 🤗 Hugging Face, 📁 GitHub)
- **Preset System**: Save and load model configurations without losing database entries
- **Improved Workflow**: Load scripts only check/uncheck models, don't replace database

### Key Features:

#### 🗄️ **Global Model Database**
- All models ever added are stored permanently in `model_database.json`
- Database persists across sessions and grows over time
- No more losing models when loading different scripts
- Currently supports 10+ model categories with 35+ models

#### 🎯 **Smart Model Identification**
- **CivitAI Models**: `🎨 RealVisXL V5.0 (V5.0 Lightning) by Creator`
- **Hugging Face Models**: `🤗 sd_xl_base_1.0_0.9vae.safetensors`
- **GitHub Repos**: `📁 rgthree/rgthree-comfy`
- **Google Drive**: `💾 model_filename.safetensors`
- **OneDrive/SharePoint**: `☁️ model_filename.pth`
- **Dropbox**: `📦 model_filename.ckpt`
- **Direct URLs**: `🔗 annotator_model.pth`
- **Unique Names**: No more confusing entries - each model shows specific filename with platform indicator

#### 📋 **Enhanced Preset System**
- Presets only check/uncheck models, don't replace database
- **SDXL Complete Setup** preset included with 15+ professional models
- Save custom presets for different workflows
- Load presets without losing your model collection

#### 🔍 **Model Search Integration**
- Built-in search for CivitAI and Hugging Face models
- Browse and add models directly from the GUI
- Automatic metadata fetching and smart naming

### Interface Overview:

**Main Buttons:**
- `📂 Load Script` - Load .sh script and check matching models in database
- `💾 Save Script` - Generate script with only checked models
- `🚀 Upload to Git` - Save as default.sh and commit to repository
- `📋 Presets ▼` - Load saved preset configurations
- `🗑️ Clear All` - Uncheck all models in database

**Categories:**
- ⚙️ Settings (parallel downloads)
- 📦 APT/PIP Packages
- 🔧 ComfyUI Nodes & Workflows
- 🎯 Model Types: Checkpoints, UNET, Diffusion
- 🎨 Creative: LoRA, VAE, ControlNet
- ⬆️ Upscaling: ESRGAN, Upscale Models
- 🔍 Utilities: Annotators, CLIP Vision, Text Encoders

### Installation & Usage:

```bash
# Install dependencies
pip install PySide6 requests

# Run the GUI
python provisioning_gui.py
```

### Workflow:

#### New Users:
1. Launch GUI - loads global database (shows all available models)
2. Check models you want for your setup
3. Save script or use presets

#### Existing Users:
1. Load existing script - only checks matching models, keeps database intact
2. Add new models - they're added to global database permanently
3. Use presets to switch between different configurations
4. Export scripts with only checked models

#### Advanced Features:
- **Search Models**: Find and add models from CivitAI/Hugging Face directly
- **Batch Operations**: Check/uncheck all models in a category
- **Model Comments**: Generated scripts include human-readable model names as comments
- **Auto-Save**: Database automatically saves as you make changes

### Generated Script Format:

```bash
CHECKPOINT_MODELS=(
    "https://civitai.com/api/download/models/798204" # 🎨 RealVisXL V5.0 (V5.0 Lightning) by Creator
    "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0_0.9vae.safetensors" # 🤗 sd_xl_base_1.0_0.9vae.safetensors
)

UPSCALE_MODELS=(
    "https://huggingface.co/uwg/upscaler/resolve/main/ESRGAN/4x-UltraSharp.pth" # 🤗 4x-UltraSharp.pth
    "https://huggingface.co/uwg/upscaler/resolve/main/ESRGAN/4x_NMKD-Siax_200k.pth" # 🤗 4x_NMKD-Siax_200k.pth
)
```

The GUI transforms cryptic URLs into meaningful, identifiable model names while maintaining full functionality!