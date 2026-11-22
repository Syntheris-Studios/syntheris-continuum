"""Verify the application venv and exercise the selected compute device."""
import sys

if sys.prefix == sys.base_prefix:
    raise SystemExit("Run this check using the application's .venv Python.")
if sys.version_info[:2] != (3, 11):
    raise SystemExit("Python 3.11 is required.")

import numpy
import torch
import gradio
import cv2

print("Imports OK:", numpy.__version__, torch.__version__, gradio.__version__, cv2.__version__)
device = "cuda" if torch.cuda.is_available() else "cpu"
x = torch.ones((2, 2), device=device)
assert torch.equal(x @ x, torch.full((2, 2), 2.0, device=device))
if device == "cuda":
    torch.cuda.synchronize()
    print("GPU kernel check OK:", torch.cuda.get_device_name(0))
else:
    print("CPU kernel check OK; CUDA is unavailable on this machine.")
