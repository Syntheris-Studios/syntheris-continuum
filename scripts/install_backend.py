import argparse, os, subprocess, sys, shutil


def sh(cmd, check=True):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"cmd failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout[-4000:]}")
    return p


def have_nvidia() -> bool:
    return shutil.which("nvidia-smi") is not None and sh(["nvidia-smi"], check=False).returncode == 0


def pip_install(pkgs, index_url=None):
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Backend installation requires a venv. Run setup.bat first.")
    cmd = [sys.executable, "-m", "pip", "install"]
    if index_url:
        cmd += ["--index-url", index_url]
    cmd += pkgs
    return sh(cmd, check=True)


def install_rife(gpu: bool | None):
    if gpu is None:
        gpu = have_nvidia()
    if gpu:
        print("[RIFE] Installing PyTorch (CUDA 12.8 wheels)â€¦")
        pip_install(["torch==2.7.1+cu128", "torchvision==0.22.1+cu128", "torchaudio==2.7.1+cu128"], index_url="https://download.pytorch.org/whl/cu128")
    else:
        print("[RIFE] Installing PyTorch CPU wheelsâ€¦")
        pip_install(["torch==2.7.1", "torchvision==0.22.1", "torchaudio==2.7.1"], index_url="https://download.pytorch.org/whl/cpu")
    # verify
    try:
        import importlib.util
        ok = importlib.util.find_spec("torch") is not None
        if not ok:
            raise ImportError("torch not found after install")
        import torch  # noqa
        print(f"[RIFE] PyTorch ready. CUDA available={torch.cuda.is_available()}")
    except Exception as e:
        raise SystemExit(f"[RIFE] Verification failed: {e}")


def main():
    ap = argparse.ArgumentParser(description="Install/repair the RIFE backend in the current venv")
    ap.add_argument("--rife", action="store_true", help="Install RIFE backend (PyTorch)")
    ap.add_argument("--auto", action="store_true", help="Install RIFE if missing (default)")
    ap.add_argument("--cpu", action="store_true", help="Force RIFE CPU wheels")
    args = ap.parse_args()
    import importlib.util
    if not args.rife and importlib.util.find_spec("torch") is not None:
        print("[AUTO] RIFE backend already present. Nothing to do.")
        return
    install_rife(gpu=False if args.cpu else None)
    print("[DONE] RIFE backend installed/verified.")


if __name__ == "__main__":
    main()
