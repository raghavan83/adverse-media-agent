# AMD ROCm Local Model Setup

This guide helps you enable local LLM inference for the Adverse Media Screening Copilot on AMD hardware.

## 1. Check ROCm availability
Run these commands on the AMD machine:

```bash
/opt/rocm/bin/rocminfo | head
rocm-smi
python -c "import torch; print(torch.cuda.is_available())"
```

ROCm documentation recommends verifying GPU visibility before model setup, and PyTorch ROCm installs should report GPU availability through `torch.cuda.is_available()` when configured correctly.

## 2. Create Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

AMD ROCm guidance for Hugging Face inference uses a Python virtual environment plus ROCm-enabled PyTorch and Transformers.

## 3. Install ROCm-enabled PyTorch
Use the correct ROCm wheel for your machine. AMD and Hugging Face guidance both point to installing PyTorch with the ROCm-specific index URL.

Example:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2
```

If your environment uses a different ROCm version, use the matching wheel command from PyTorch or AMD documentation.

## 4. Install Transformers stack
```bash
pip install transformers accelerate huggingface-hub
```

Optional login for gated models:
```bash
hf auth login
```

## 5. Configure the project
Edit `.env`:
```env
ENABLE_LOCAL_LLM=true
LLM_PROVIDER=local
LLM_MODEL=Qwen/Qwen2.5-3B-Instruct
MAX_NEW_TOKENS=256
TEMPERATURE=0.1
```

## 6. Run health check
Start the backend and call `/health`.
You should see local LLM configuration values and can then run a screening case to verify that the agent tasks use the local model.

## 7. Recommended hackathon model choices
For practical local inference, use a smaller instruct model first, such as a 3B class model, before trying larger models. This reduces bring-up risk while still demonstrating true LLM-backed agent tasks.

## 8. Docker option
AMD ROCm documentation also provides a ROCm-enabled PyTorch Docker workflow. That is useful when your host environment is inconsistent.
