import json
import shutil
import subprocess
import time
from typing import Any, Dict, Optional


def now_ms() -> int:
    return int(time.time() * 1000)


def safe_json_loads(value: str):
    try:
        return json.loads(value)
    except Exception:
        return value


def detect_gpu_tool() -> Optional[str]:
    if shutil.which("rocm-smi"):
        return "rocm-smi"
    if shutil.which("nvidia-smi"):
        return "nvidia-smi"
    return None


def get_gpu_stats() -> Dict[str, Any]:
    tool = detect_gpu_tool()
    if tool == "rocm-smi":
        commands = [
            ["rocm-smi", "--showproductname", "--showuse", "--showmemuse", "--json"],
            ["rocm-smi", "-i", "--showproductname", "--showuse", "--showmemuse", "--json"],
        ]
        for cmd in commands:
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
                return {"tool": tool, "raw": safe_json_loads(out)}
            except Exception:
                continue
        return {"tool": tool, "raw": None, "error": "unable to collect rocm-smi stats"}
    if tool == "nvidia-smi":
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                text=True,
                stderr=subprocess.STDOUT,
            ).strip()
            return {"tool": tool, "raw": out}
        except Exception as exc:
            return {"tool": tool, "raw": None, "error": str(exc)}
    return {"tool": None, "raw": None, "error": "no supported gpu tool found"}


def calc_tokens_per_second(response_tokens: int, duration_ms: int) -> float:
    if not duration_ms or duration_ms <= 0:
        return 0.0
    return round(response_tokens / (duration_ms / 1000.0), 2)
