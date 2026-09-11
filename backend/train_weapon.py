"""
Automated Weapon Detection Model Fine-Tuning Pipeline.

Features:
- Downloads sample weapon CCTV dataset if no local dataset exists.
- Generates YOLO-compliant dataset.yaml.
- Loads existing threat-yolov8n.pt weights.
- Fine-tunes model on CPU or GPU with customizable epochs and batch size.
- Updates models/weapon/threat-yolov8n.pt with new best weights (preserving backup).
"""
import os
import sys
import shutil
import urllib.request
from pathlib import Path
import yaml
from ultralytics import YOLO

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / "models" / "weapon" / "threat-yolov8n.pt"
DATASET_DIR = ROOT_DIR / "data" / "weapon_dataset"
YAML_PATH = DATASET_DIR / "dataset.yaml"


def download_sample_dataset():
    """Downloads sample CCTV weapon images and annotations from open repository if missing."""
    images_dir = DATASET_DIR / "images"
    labels_dir = DATASET_DIR / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    base_url = "https://huggingface.co/datasets/Simuletic/cctv-weapon-dataset/raw/main"
    base_lfs_url = "https://huggingface.co/datasets/Simuletic/cctv-weapon-dataset/resolve/main"

    sample_files = [
        "Scene1_1", "Scene1_2", "Scene1_3", "Scene1_4", "Scene1_5",
        "Scene2_1", "Scene2_2", "Scene2_3", "Scene2_4", "Scene2_5",
    ]

    print(f"[Dataset] Checking dataset in {DATASET_DIR}...")
    existing_images = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
    if len(existing_images) >= len(sample_files):
        print(f"[Dataset] Found {len(existing_images)} existing images. Skipping download.")
        return

    print("[Dataset] Fetching CCTV weapon samples...")
    for name in sample_files:
        img_dest = images_dir / f"{name}.png"
        lbl_dest = labels_dir / f"{name}.txt"

        if not img_dest.exists():
            try:
                urllib.request.urlretrieve(f"{base_lfs_url}/samples/images/{name}.png", str(img_dest))
            except Exception as e:
                print(f"  Warning: failed to download image {name}: {e}")

        if not lbl_dest.exists():
            try:
                urllib.request.urlretrieve(f"{base_url}/samples/labels/{name}.txt", str(lbl_dest))
            except Exception as e:
                print(f"  Warning: failed to download label {name}: {e}")

    count = len(list(images_dir.glob("*.png")))
    print(f"[Dataset] Ready with {count} annotated images.")


def create_dataset_yaml():
    """Generates dataset.yaml pointing to the dataset directory."""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    images_path = str((DATASET_DIR / "images").resolve()).replace("\\", "/")

    data = {
        "path": str(DATASET_DIR.resolve()).replace("\\", "/"),
        "train": "images",
        "val": "images",
        "names": {
            0: "Gun",
            1: "Explosion",
            2: "Grenade",
            3: "Knife",
        }
    }
    with open(YAML_PATH, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    print(f"[Dataset] Created config at {YAML_PATH}")


def fine_tune(epochs: int = 5, batch: int = 4, device: str = "cpu"):
    """Runs fine-tuning on threat-yolov8n.pt."""
    download_sample_dataset()
    create_dataset_yaml()

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Source model not found at {MODEL_PATH}")

    print(f"\n[Fine-Tune] Loading model from: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))

    print(f"[Fine-Tune] Starting training: epochs={epochs}, batch={batch}, device={device}")
    results = model.train(
        data=str(YAML_PATH),
        epochs=epochs,
        batch=batch,
        imgsz=640,
        device=device,
        project=str(ROOT_DIR / "runs" / "weapon_train"),
        name="finetune",
        exist_ok=True,
        verbose=True,
    )

    best_pt = ROOT_DIR / "runs" / "weapon_train" / "finetune" / "weights" / "best.pt"
    if best_pt.exists():
        backup_path = MODEL_PATH.with_suffix(".pt.bak")
        print(f"\n[Fine-Tune] Backing up current model to: {backup_path}")
        shutil.copy2(MODEL_PATH, backup_path)

        print(f"[Fine-Tune] Deploying new fine-tuned weights to: {MODEL_PATH}")
        shutil.copy2(best_pt, MODEL_PATH)
        print("[Fine-Tune] Deployment SUCCESSFUL!")
    else:
        print(f"[Fine-Tune] Warning: {best_pt} not found, keeping existing model.")

    return results


if __name__ == "__main__":
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    batch = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    fine_tune(epochs=epochs, batch=batch, device="cpu")
