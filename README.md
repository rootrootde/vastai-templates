# Vast.ai Provisioning Templates

Automated provisioning scripts for Vast.ai GPU instances with ComfyUI and AI models.

## Quick Start

1. Use one of the provisioning scripts (e.g., `default.sh`) as your startup script in Vast.ai
2. Set environment variables `HF_TOKEN` and/or `CIVITAI_TOKEN` for private model access
3. The script automatically installs packages, ComfyUI nodes, and downloads models

## GUI Tool

A graphical interface is available for creating custom provisioning scripts:

```bash
pip install -r requirements.txt
python provisioning_gui.py
```

### Features:
- Visual management of all provisioning options
- Real-time script preview
- Direct Git integration for uploading scripts
- Load and edit existing scripts

## Script Structure

Provisioning scripts configure:
- **APT Packages**: System-level dependencies
- **PIP Packages**: Python packages
- **ComfyUI Nodes**: Custom nodes from GitHub
- **AI Models**: Various model types downloaded to appropriate directories
  - Checkpoints → `/models/checkpoints`
  - LoRA → `/models/lora`
  - VAE → `/models/vae`
  - Upscale → `/models/upscale_models`
  - ControlNet → `/models/controlnet`
  - And more...

## Authentication

For private or gated models:
- Set `HF_TOKEN` for Hugging Face models
- Set `CIVITAI_TOKEN` for CivitAI models

## Customization

Edit the arrays at the top of any provisioning script to customize what gets installed. Or use the GUI tool for a more user-friendly experience.