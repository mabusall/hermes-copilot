# Router Dependency Installation Guide

This directory contains the package specifications for each of the three System 1 Router editions.

> [!TIP]
> If you are using the automated switcher script (`scripts/switch_router.sh`), you **do not need to install these manually**—the script automatically creates the isolated virtual environment and installs the right file for you.

---

## How to Install Manually

If you prefer installing dependencies manually using `pip` or `uv`:

### 1. Semantic Router (Default & Recommended)
* **File:** [`semantic.txt`](semantic.txt)
* **Footprint:** ~340 MB RAM (ONNX Runtime, zero PyTorch required)
* **Command:**
  ```bash
  pip install -r requirements/semantic.txt
  ```

---

### 2. Laya
* **File:** [`laya.txt`](laya.txt)
* **Footprint:** ~2.0 GB RAM (CPU-only PyTorch + 421M ModernBERT)
* **Command:**
  ```bash
  pip install -r requirements/laya.txt
  ```

---

### 3. RouteLLM
* **File:** [`routellm.txt`](routellm.txt)
* **Footprint:** ~1.2 GB RAM (CPU-only PyTorch + BERT Classifier)
* **Command:**
  ```bash
  pip install -r requirements/routellm.txt
  ```
