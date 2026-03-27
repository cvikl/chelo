"""
Glacier segmentation model loader with DL4GAM-correct normalization.

Loads the trained UNet (ResNet34 encoder, 16 input channels, 1 output class)
and applies the exact normalization the model was trained with.
"""

import os
import torch
import numpy as np
import segmentation_models_pytorch as smp

CKPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ckpt-epoch=29-w_JaccardIndex_val_epoch_avg_per_g=0.8935.ckpt",
)

# Normalization constants from DL4GAM training
OPTICAL_MEAN = 0.25
OPTICAL_STD = 0.20
DEM_MEAN = 2700.0     # Mean elevation of training glaciers (metres)
DHDT_MEAN = -0.3      # Mean elevation change rate in Alps (m/yr)
SLOPE_MAX = 90.0      # Slope scaled to [0, 1]

_model = None


def get_model():
    """Load the glacier segmentation model (lazy, cached)."""
    global _model
    if _model is not None:
        return _model

    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None,
        in_channels=16,
        classes=1,
        decoder_use_batchnorm=False,
    )

    ckpt = torch.load(CKPT_PATH, map_location="cpu", weights_only=False)
    state_dict = ckpt["state_dict"]

    cleaned = {}
    for k, v in state_dict.items():
        if k.startswith("model.seg_model."):
            cleaned[k.replace("model.seg_model.", "")] = v

    model.load_state_dict(cleaned)
    model.eval()
    _model = model
    return model


def normalize_input(stack16: np.ndarray) -> torch.Tensor:
    """
    Apply DL4GAM-correct normalization to a 16-band stack.

    Input: numpy array (16, H, W) with:
      - Bands 0-12: Sentinel-2 reflectance [0-1]
      - Band 13: DEM elevation (metres)
      - Band 14: dh/dt (m/yr), zeros if unavailable
      - Band 15: Slope (degrees 0-90)

    Returns: torch tensor (1, 16, H, W) ready for model inference.
    """
    normalized = stack16.copy()

    # Optical bands: Z-score with global Alps statistics
    normalized[:13] = (normalized[:13] - OPTICAL_MEAN) / OPTICAL_STD

    # DEM: subtract mean only (NOT divided by std)
    normalized[13] = normalized[13] - DEM_MEAN

    # dh/dt: subtract mean only
    normalized[14] = normalized[14] - DHDT_MEAN

    # Slope: scale to [0, 1]
    normalized[15] = normalized[15] / SLOPE_MAX

    return torch.from_numpy(normalized).unsqueeze(0).float()


def predict_glacier_mask(stack16: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Run glacier segmentation on a 16-band stack.

    Args:
        stack16: numpy array (16, H, W) — raw values, will be normalized internally.

    Returns:
        (mask, probs): binary mask (H, W) uint8, probability map (H, W) float32
    """
    model = get_model()
    tensor = normalize_input(stack16)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.sigmoid(logits).squeeze().cpu().numpy()
        mask = (probs > 0.5).astype(np.uint8)

    return mask, probs


def calculate_glacier_area(mask: np.ndarray, pixel_size_m: float = 10.0) -> float:
    """Calculate glacier area in km² from a binary mask."""
    glacier_pixels = mask.sum()
    area_m2 = glacier_pixels * pixel_size_m * pixel_size_m
    return area_m2 / 1_000_000
