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

### 📋 Script-Based Presets
- **No Separate Preset Files**: Use .sh scripts directly as presets
- **Example Presets**: SDXL workflows included in `/presets/` directory
- **Easy Sharing**: Preset files are standard shell scripts
- **Version Control Friendly**: Track preset changes with git

## 🎮 GUI Interface

### Main Controls
| Button | Function |
|--------|----------|
| 📂 Load Preset | Load .sh preset file and check matching models |
| 💾 Save Preset | Save current selection as .sh preset file |
| 🚀 Upload to Git | Save as default.sh and commit |
| 🗑️ Clear All | Uncheck all models |
| 🔄 Refresh Names | Update model names from APIs |

### Model Categories
- **🎯 Checkpoints**: Base models and refiners
- **🎨 Creative**: LoRA, VAE, ControlNet models
- **⬆️ Upscaling**: ESRGAN and upscale models
- **🔧 Tools**: ComfyUI nodes and workflows
- **🔍 Utilities**: Annotators, CLIP vision, text encoders

## 📁 File Structure

```
├── provisioning_gui.py      # Main GUI application
├── default.sh               # Active provisioning script
├── template.sh             # Script template
├── model_database.json     # Global model database
├── presets/                # Preset script files
│   ├── sdxl-complete-setup.sh
│   └── sdxl.sh
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

## 📋 Included Preset Scripts

### `presets/sdxl-complete-setup.sh`
Professional SDXL workflow including:
- **Base Models**: SDXL 1.0 Base + Refiner (13 GB)
- **VAE**: Fixed SDXL VAE for fp16 (335 MB)
- **LoRA**: Offset Noise LoRA (50 MB)
- **Upscalers**: 4x-UltraSharp, NMKD-Siax, Nickelback (201 MB)
- **ControlNet**: Canny, Depth, Recolor, Sketch (3 GB)
- **Utilities**: Annotators, CLIP Vision (3.7 GB)

### `presets/sdxl.sh`
Streamlined SDXL setup with essential models and ComfyUI nodes.

**Usage**: Load any `.sh` preset file in the GUI to apply its configuration.

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