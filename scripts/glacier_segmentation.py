import torch
import numpy as np
import rasterio
from seg_model import SegModelSMP
import os
import matplotlib.pyplot as plt

# ================= CONFIGURATION =================
CHECKPOINT_PATH = "../models/ckpt-epoch=29-w_JaccardIndex_val_epoch_avg_per_g=0.8935.ckpt"
INPUT_TIF = "test_16band_stack.tif"

# Exactly 16 channels to match the checkpoint
INPUT_SETTINGS = {
    'bands_input': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B10', 'B11', 'B12'], # 13
    'optical_indices': [], # 0
    'dem': True,           # 1
    'dem_features': ['slope'], # 1
    'dhdt': True,          # 1
    'velocity': False      # 0
} # Total = 16
# =================================================

def prepare_16channel_batch(tif_path):
    """Reads the 16-band TIFF and packages it into the dict expected by the model."""
    with rasterio.open(tif_path) as src:
        data = src.read().astype(np.float32)
    
    # 1. Optical Bands (1-13)
    # The saved TIFF has reflectances in [0, 1]. The model was trained with 'standardize_data=True'.
    # We use approximate *global* Alps stats instead of instance (per-image) stats. 
    # Z-scoring per image stretches dark cities to look bright (like snow), causing false positives.
    band_tensor = torch.from_numpy(data[0:13]).unsqueeze(0)
    global_b_mean = 0.25 
    global_b_std = 0.20
    band_tensor = (band_tensor - global_b_mean) / global_b_std

    # 2. DEM (Band 14)
    # IMPORTANT: Looking at `dl4gam_alps/pl_modules/data.py` line 145, 
    # the training code *only subtracts the mean* for DEM—it does NOT divide by std!
    # By dividing by std previously, we gave the model values between [-3, 3] which 
    # it interpreted as elevation around 2700m (its mean), making the city look like a mountain!
    dem_tensor = torch.from_numpy(data[13]).unsqueeze(0) # shape (1, H, W)
    dem_global_mean = 2700.0  # approximate mean elevation of training glaciers
    dem_tensor = dem_tensor - dem_global_mean
    
    # 3. DHDT (Band 15)
    # Normally provided by an external Hugonnet GeoTIFF. Mean in Alps is typically ~ -0.3 m/yr.
    # Training code also only subtracts the mean here. We pass empty 0s but subtract the mean
    # so the model receives typical neutral values.
    dhdt_tensor = torch.from_numpy(data[14]).unsqueeze(0) # shape (1, H, W)
    dhdt_global_mean = -0.3 
    dhdt_tensor = dhdt_tensor - dhdt_global_mean

    # 4. Slope (Band 16)
    # The model's data loader explicitly scaled slope to [0, 1] by dividing by 90.
    slope_tensor = torch.from_numpy(data[15]).unsqueeze(0) / 90.0 # shape (1, H, W)

    batch = {
        'band_data': band_tensor,
        'dem': dem_tensor,
        'dhdt': dhdt_tensor,
        'slope': slope_tensor
    }
    return batch

def run_dl4gam(input_tif=None):
    if input_tif is None:
        input_tif = INPUT_TIF

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Initialize model
    model = SegModelSMP(
        input_settings=INPUT_SETTINGS,
        other_settings=None,
        model_name="Unet",
        model_args={'encoder_name': 'resnet34', 'classes': 1, 'encoder_weights': None}
    )

    # 2. Load Weights (Fixing the prefix issue and using strict=False)
    print("Loading weights...")
    ckpt = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    state_dict = {}
    for k, v in ckpt['state_dict'].items():
        if k.startswith("model."):
            state_dict[k[6:]] = v # Remove exactly "model." (6 characters)
        else:
            state_dict[k] = v
            
    # strict=False allows us to ignore minor missing bias/norm keys in the decoder
    model.load_state_dict(state_dict, strict=False)
    model.to(device).eval()

    # 3. Inference
    print(f"Reading {input_tif}...")
    batch = prepare_16channel_batch(input_tif)
    batch = {k: v.to(device) for k, v in batch.items()}
    
    # Store original data for plotting RGB
    with rasterio.open(input_tif) as src:
        original_data = src.read().astype(np.float32)

    print("Running segmentation...")
    with torch.no_grad():
        logits = model(batch)
        probs = torch.sigmoid(logits).squeeze().cpu().numpy()
        mask = (probs > 0.5).astype(np.uint8)
    
    return mask
    # # 4. Quick Visualization
    # plt.figure(figsize=(10, 5))
    # plt.subplot(1, 2, 1)
    # # Show bands B4, B3, B2 (Red, Green, Blue) which are indices 3, 2, 1
    # rgb = original_data[[3, 2, 1], :, :]
    # rgb = np.moveaxis(rgb, 0, -1)
    
    # # Improve Sentinel-2 True Color Visualization
    # # Reflectance values above 0.3 usually represent clouds or very bright snow,
    # # stretching the [0, 0.3] range to [0, 1] yields a much more natural image.
    # rgb = np.clip(rgb / 0.3, 0, 1)
    
    # plt.imshow(rgb)
    # plt.title("Input RGB (Mock Data)")
    
    # plt.subplot(1, 2, 2)
    # plt.imshow(mask, cmap="Blues", vmin=0, vmax=1)
    # plt.title("Predicted Glacier Mask")
    
    # plt.savefig("result_preview.png")
    # print("Segmentation complete. Saved preview to 'result_preview.png'")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run DL4GAM segmentation inference")
    parser.add_argument("--input_tif", type=str, help="Path to the input 16-band TIFF file")
    args = parser.parse_args()

    run_dl4gam(input_tif=args.input_tif)