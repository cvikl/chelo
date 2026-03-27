"""
Glacier segmentation model loader.

Loads the trained UNet (ResNet34 encoder, 16 input channels, 1 output class)
from a PyTorch Lightning checkpoint for Sentinel-2 glacier segmentation.
"""

import os
import torch
import segmentation_models_pytorch as smp

CKPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ckpt-epoch=29-w_JaccardIndex_val_epoch_avg_per_g=0.8935.ckpt",
)

_model = None


def get_model():
    """Load the glacier segmentation model (lazy, cached)."""
    global _model
    if _model is not None:
        return _model

    # Recreate the architecture: UNet with ResNet34, 16 input channels, 1 class
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None,
        in_channels=16,
        classes=1,
        decoder_use_batchnorm=False,
    )

    # Load weights from checkpoint
    ckpt = torch.load(CKPT_PATH, map_location="cpu", weights_only=False)
    state_dict = ckpt["state_dict"]

    # Strip "model.seg_model." prefix from keys
    cleaned = {}
    for k, v in state_dict.items():
        if k.startswith("model.seg_model."):
            cleaned[k.replace("model.seg_model.", "")] = v

    model.load_state_dict(cleaned)
    model.eval()
    _model = model
    return model


def predict_glacier_mask(image_tensor: torch.Tensor) -> torch.Tensor:
    """
    Run glacier segmentation on a Sentinel-2 image tensor.

    Args:
        image_tensor: shape (1, 16, H, W) — 16-band Sentinel-2 tile, normalized.

    Returns:
        Binary mask tensor (1, 1, H, W) — 1 = glacier, 0 = no glacier.
    """
    model = get_model()
    with torch.no_grad():
        logits = model(image_tensor)
        mask = (torch.sigmoid(logits) > 0.5).float()
    return mask


def calculate_glacier_area(mask: torch.Tensor, pixel_size_m: float = 10.0) -> float:
    """
    Calculate glacier area in km² from a binary mask.

    Args:
        mask: Binary mask (1, 1, H, W)
        pixel_size_m: Pixel resolution in meters (default 10m for Sentinel-2)

    Returns:
        Area in km²
    """
    glacier_pixels = mask.sum().item()
    area_m2 = glacier_pixels * pixel_size_m * pixel_size_m
    return area_m2 / 1_000_000
