# Vast.ai Provisioning Templates

Advanced provisioning templates for Vast.ai GPU instances with ComfyUI setup automation.

## 🚀 Quick Start

### GUI Tool (Recommended)
```bash
# Install dependencies
pip install PySide6 requests

# Launch GUI
python provisioning_gui.py
```

### Manual Script Editing
Edit `default.sh` directly and add URLs to the appropriate arrays.

## ✨ Key Features

### 🎯 Smart Model Names
No more cryptic URLs! The GUI automatically identifies models:

- **🎨 CivitAI**: `RealVisXL V5.0 (V5.0 Lightning) by Creator`
- **🤗 Hugging Face**: `sd_xl_base_1.0_0.9vae.safetensors`  
- **📁 GitHub**: `rgthree/rgthree-comfy`

### 🗄️ Global Model Database
- **Persistent Storage**: Never lose models when loading different scripts
- **Growing Collection**: Database expands as you add more models
- **Smart Workflow**: Scripts only check/uncheck models, don't replace database

### 📋 Enhanced Presets
- **SDXL Complete Setup**: Professional SDXL workflow with 15+ models
- **Custom Presets**: Save your own model configurations
- **Non-Destructive**: Presets only change selections, keep your full database

## 🎮 GUI Interface

### Main Controls
| Button | Function |
|--------|----------|
| 📂 Load Script | Import .sh file and check matching models |
| 💾 Save Script | Export script with checked models |
| 🚀 Upload to Git | Save as default.sh and commit |
| 📋 Presets ▼ | Load/save preset configurations |
| 🗑️ Clear All | Uncheck all models |

### Model Categories
- **🎯 Checkpoints**: Base models and refiners
- **🎨 Creative**: LoRA, VAE, ControlNet models
- **⬆️ Upscaling**: ESRGAN and upscale models
- **🔧 Tools**: ComfyUI nodes and workflows
- **🔍 Utilities**: Annotators, CLIP vision, text encoders

## 📁 File Structure

```
├── provisioning_gui.py      # Main GUI application
├── default.sh               # Generated provisioning script
├── template.sh             # Script template
├── model_database.json     # Global model database
├── presets.json           # Saved presets
└── CLAUDE.md             # Development documentation
```

## 🔧 Technical Details

### Supported Platforms
- **CivitAI**: Automatic metadata fetching with creator info
- **Hugging Face**: Repository and filename extraction
- **GitHub**: Repository identification for ComfyUI nodes

### Authentication
Set environment variables for private model access:
- `HF_TOKEN` - Hugging Face token
- `CIVITAI_TOKEN` - CivitAI token

### Parallel Downloads
Configure `MAX_PARALLEL_DOWNLOADS` in settings (default: 4)

## 📋 Included Presets

### SDXL Complete Setup
Professional SDXL workflow including:
- **Base Models**: SDXL 1.0 Base + Refiner (13 GB)
- **VAE**: Fixed SDXL VAE for fp16 (335 MB)
- **LoRA**: Offset Noise LoRA (50 MB)
- **Upscalers**: 4x-UltraSharp, NMKD-Siax, Nickelback (201 MB)
- **ControlNet**: Canny, Depth, Recolor, Sketch (3 GB)
- **Utilities**: Annotators, CLIP Vision (3.7 GB)

**Total**: ~17.8 GB download

## 🛠️ Development

See `CLAUDE.md` for detailed development documentation and architecture overview.

## 📝 Generated Script Example

```bash
CHECKPOINT_MODELS=(
    "https://civitai.com/api/download/models/798204" # 🎨 RealVisXL V5.0 by Creator
    "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0_0.9vae.safetensors" # 🤗 sd_xl_base_1.0_0.9vae.safetensors
)

UPSCALE_MODELS=(
    "https://huggingface.co/uwg/upscaler/resolve/main/ESRGAN/4x-UltraSharp.pth" # 🤗 4x-UltraSharp.pth
)
```

The GUI transforms cryptic URLs into meaningful, identifiable model names while maintaining full functionality for Vast.ai provisioning!