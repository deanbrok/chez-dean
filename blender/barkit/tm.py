"""Shared tone mapping: linear scene-referred float RGB -> display sRGB uint8 (same curve for previews and bakes)."""
import numpy as np
from PIL import Image
EXPOSURE = 1.25

def curve(x):
    # ACES-like filmic fit (Narkowicz), slightly lifted toe so shadows keep some detail
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)

def srgb(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 1e-8), 1 / 2.4) - 0.055)

def tonemap(lin, exposure=None):
    x = np.maximum(lin, 0) * (EXPOSURE if exposure is None else exposure)
    # keep hue of very bright warm lights: blend per-channel curve with luminance-preserving curve
    l = (x * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    y1 = curve(x)
    y2 = x * (curve(l) / np.maximum(l, 1e-6))
    y = np.clip(0.6 * y1 + 0.4 * np.clip(y2, 0, 1), 0, 1)
    return srgb(y)

def save(lin, path, exposure=None, quality=90):
    im = Image.fromarray((tonemap(lin, exposure) * 255 + 0.5).astype(np.uint8))
    im.save(path, quality=quality)
    l = (lin * np.array([0.2126, 0.7152, 0.0722])).sum(-1)
    print('lum percentiles 10/50/90/99:', [round(float(v), 4) for v in np.percentile(l, [10, 50, 90, 99])])
