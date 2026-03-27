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


def predict_glacier_mask(stack16):
    """
    Run glacier segmentation on a 16-band stack.

    Args:
        stack16: numpy array (16, H, W) — reflectance [0-1] + DEM + dhdt + slope.

    Returns:
        (mask, probs): binary mask (H, W) uint8, probability map (H, W) float32
    """
    model = get_model()
    tensor = torch.from_numpy(stack16).unsqueeze(0).float()

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.sigmoid(logits).squeeze().cpu().numpy()
        mask = (probs > 0.5).astype('uint8')

    return mask, probs


def calculate_glacier_area(mask, pixel_size_m=10.0):
    """Calculate glacier area in km2 from a binary mask."""
    glacier_pixels = mask.sum()
    area_m2 = glacier_pixels * pixel_size_m * pixel_size_m
    return area_m2 / 1_000_000
