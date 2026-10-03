"""Provide non-persistent standard streams for Windows pythonw dependencies."""
import os
import sys


def ensure_standard_streams():
    # pythonw supplies None. Torch/tqdm model downloads still call stderr.write.
    # NUL prevents crashes without retaining library output or user content.
    for name, mode in (("stdout", "w"), ("stderr", "w"), ("stdin", "r")):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, mode, encoding="utf-8"))
