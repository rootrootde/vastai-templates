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