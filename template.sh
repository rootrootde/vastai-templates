#!/bin/bash

source /venv/main/bin/activate
COMFYUI_DIR=${WORKSPACE}/ComfyUI

# Packages are installed after nodes so we can fix them...

APT_PACKAGES=(
{apt_packages}
)

PIP_PACKAGES=(
{pip_packages}
)

NODES=(
{nodes}
)

WORKFLOWS=(
{workflows}
)

CHECKPOINT_MODELS=(
{checkpoint_models}
)

UNET_MODELS=(
{unet_models}
)

LORA_MODELS=(
{lora_models}
)

VAE_MODELS=(
{vae_models}
)

ESRGAN_MODELS=(
{esrgan_models}
)

UPSCALE_MODELS=(
{upscale_models}
)

CONTROLNET_MODELS=(
{controlnet_models}
)

ANNOTATOR_MODELS=(
{annotator_models}
)

CLIP_VISION_MODELS=(
{clip_vision_models}
)


function provisioning_start() {
    provisioning_print_header
    provisioning_get_apt_packages
    provisioning_get_nodes
    provisioning_get_pip_packages
    provisioning_get_workflows
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/checkpoints" \\
        "${CHECKPOINT_MODELS[@]}"
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/unet" \\
        "${UNET_MODELS[@]}"
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/lora" \\
        "${LORA_MODELS[@]}"
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/controlnet" \\
        "${CONTROLNET_MODELS[@]}"
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/vae" \\
        "${VAE_MODELS[@]}"
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/esrgan" \\
        "${ESRGAN_MODELS[@]}"
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/upscale_models" \\
        "${UPSCALE_MODELS[@]}"
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/annotators" \\
        "${ANNOTATOR_MODELS[@]}"
    provisioning_get_files \\
        "${COMFYUI_DIR}/models/clip_vision" \\
        "${CLIP_VISION_MODELS[@]}"
    provisioning_print_end
}

function provisioning_get_apt_packages() {
    if [[ -n $APT_PACKAGES ]]; then
            sudo $APT_INSTALL ${APT_PACKAGES[@]}
    fi
}

function provisioning_get_pip_packages() {
    if [[ -n $PIP_PACKAGES ]]; then
            pip install --no-cache-dir ${PIP_PACKAGES[@]}
    fi
}

function provisioning_get_workflows() {
    if [[ ${#WORKFLOWS[@]} -eq 0 ]]; then
        return
    fi
    
    mkdir -p "${COMFYUI_DIR}/user/default/workflows"
    printf "Downloading %s workflow(s)...\\n" "${#WORKFLOWS[@]}"
    
    for url in "${WORKFLOWS[@]}"; do
        printf "Downloading workflow: %s\\n" "${url}"
        provisioning_download "${url}" "${COMFYUI_DIR}/user/default/workflows"
        printf "\\n"
    done
}

function provisioning_get_nodes() {
    for repo in "${NODES[@]}"; do
        dir="${repo##*/}"
        path="${COMFYUI_DIR}/custom_nodes/${dir}"
        requirements="${path}/requirements.txt"
        if [[ -d $path ]]; then
            if [[ ${AUTO_UPDATE,,} != "false" ]]; then
                printf "Updating node: %s...\\n" "${repo}"
                ( cd "$path" && git pull )
                if [[ -e $requirements ]]; then
                   pip install --no-cache-dir -r "$requirements"
                fi
            fi
        else
            printf "Downloading node: %s...\\n" "${repo}"
            git clone "${repo}" "${path}" --recursive
            if [[ -e $requirements ]]; then
                pip install --no-cache-dir -r "${requirements}"
            fi
        fi
    done
}

function provisioning_get_files() {
    if [[ -z $2 ]]; then return 1; fi
    
    dir="$1"
    mkdir -p "$dir"
    shift
    arr=("$@")
    printf "Downloading %s model(s) to %s...\\n" "${#arr[@]}" "$dir"
    for url in "${arr[@]}"; do
        printf "Downloading: %s\\n" "${url}"
        provisioning_download "${url}" "${dir}"
        printf "\\n"
    done
}

function provisioning_print_header() {
    printf "\\n##############################################\\n#                                            #\\n#          Provisioning container            #\\n#                                            #\\n#         This will take some time           #\\n#                                            #\\n# Your container will be ready on completion #\\n#                                            #\\n##############################################\\n\\n"
}

function provisioning_print_end() {
    printf "\\nProvisioning complete:  Application will start now\\n\\n"
}

function provisioning_has_valid_hf_token() {
    [[ -n "$HF_TOKEN" ]] || return 1
    url="https://huggingface.co/api/whoami-v2"

    response=$(curl -o /dev/null -s -w "%{http_code}" -X GET "$url" \\
        -H "Authorization: Bearer $HF_TOKEN" \\
        -H "Content-Type: application/json")

    # Check if the token is valid
    if [ "$response" -eq 200 ]; then
        return 0
    else
        return 1
    fi
}

function provisioning_has_valid_civitai_token() {
    [[ -n "$CIVITAI_TOKEN" ]] || return 1
    url="https://civitai.com/api/v1/models?hidden=1&limit=1"

    response=$(curl -o /dev/null -s -w "%{http_code}" -X GET "$url" \\
        -H "Authorization: Bearer $CIVITAI_TOKEN" \\
        -H "Content-Type: application/json")

    # Check if the token is valid
    if [ "$response" -eq 200 ]; then
        return 0
    else
        return 1
    fi
}

# Download from $1 URL to $2 file path
function provisioning_download() {
    local url="$1"
    local dest_dir="$2"
    
    if [[ -n $HF_TOKEN && $url =~ ^https://([a-zA-Z0-9_-]+\\.)?huggingface\\.co(/|$|\\?) ]]; then
        wget --header="Authorization: Bearer $HF_TOKEN" -qnc --content-disposition --show-progress -e dotbytes="${3:-4M}" -P "$dest_dir" "$url"
    elif [[ -n $CIVITAI_TOKEN && $url =~ ^https://([a-zA-Z0-9_-]+\\.)?civitai\\.com(/|$|\\?) ]]; then
        # CivitAI uses a redirect-based download system with Bearer token
        # First, get the redirect URL with authentication
        local redirect_url=$(curl -s -L -w "%{url_effective}" -o /dev/null \\
            -H "Authorization: Bearer $CIVITAI_TOKEN" \\
            -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \\
            "$url")
        
        # If we got a redirect, download from there
        if [[ -n $redirect_url && $redirect_url != $url ]]; then
            wget -qnc --content-disposition --show-progress -e dotbytes="${3:-4M}" -P "$dest_dir" "$redirect_url"
        else
            # Fallback to direct download with Bearer token
            wget --header="Authorization: Bearer $CIVITAI_TOKEN" \\
                 --header="User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \\
                 -qnc --content-disposition --show-progress -e dotbytes="${3:-4M}" -P "$dest_dir" "$url"
        fi
    else
        wget -qnc --content-disposition --show-progress -e dotbytes="${3:-4M}" -P "$dest_dir" "$url"
    fi
}

# Allow user to disable provisioning if they started with a script they didn't want
if [[ ! -f /.noprovisioning ]]; then
    provisioning_start
fi