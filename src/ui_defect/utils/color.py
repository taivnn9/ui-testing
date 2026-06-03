"""Tiện ích màu sắc: WCAG contrast, Lab conversion, màu trội."""
from __future__ import annotations

import math

import numpy as np


def srgb_to_linear(c: float) -> float:
    """Chuyển 1 channel sRGB [0,1] → linear."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG relative luminance từ sRGB tuple (0–255)."""
    r, g, b = (srgb_to_linear(v / 255.0) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """WCAG contrast ratio (1–21)."""
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """
    Chuyển mảng pixel RGB uint8 (…×3) → Lab float32.
    Dùng D65 illuminant, same as scikit-image.
    """
    # Normalize về [0,1]
    rgb_f = rgb.astype(np.float32) / 255.0
    # sRGB linearize
    mask = rgb_f <= 0.04045
    lin = np.where(mask, rgb_f / 12.92, ((rgb_f + 0.055) / 1.055) ** 2.4)
    # Linear RGB → XYZ (D65)
    M = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ], dtype=np.float32)
    xyz = lin @ M.T
    # XYZ → Lab
    ref = np.array([0.95047, 1.00000, 1.08883], dtype=np.float32)
    xyz_n = xyz / ref
    eps = 0.008856
    kappa = 903.3
    f = np.where(xyz_n > eps, xyz_n ** (1 / 3), (kappa * xyz_n + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1).astype(np.float32)


def delta_e_cie76(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """ΔE CIE76 giữa 2 màu Lab (shape (3,))."""
    return float(np.sqrt(np.sum((lab1 - lab2) ** 2)))


def _kmeans_numpy(
    data: np.ndarray,
    k: int,
    max_iter: int = 50,
    seed: int = 42,
) -> np.ndarray:
    """
    K-means thuần numpy — fallback khi không có scikit-learn.

    Khởi tạo center bằng **k-means++** (giống sklearn) thay vì random thuần:
    random init dễ bốc trúng nhiều điểm cùng màu (vd ảnh 80% nền trắng) → center
    trùng nhau → cluster rỗng → chỉ trả 1 màu (degenerate). k-means++ ưu tiên chọn
    center xa nhau nên tách được fg/bg ổn định.
    """
    rng = np.random.default_rng(seed)
    n = len(data)
    k = min(k, n)

    # ── k-means++ init ───────────────────────────────────────────────────────
    centers = np.empty((k, data.shape[1]), dtype=data.dtype)
    centers[0] = data[rng.integers(n)]
    for i in range(1, k):
        d2 = np.min(
            np.linalg.norm(data[:, None] - centers[None, :i], axis=2) ** 2, axis=1
        )
        total = float(d2.sum())
        if total <= 0:
            # mọi điểm trùng các center đã chọn → chọn ngẫu nhiên
            centers[i] = data[rng.integers(n)]
        else:
            centers[i] = data[rng.choice(n, p=d2 / total)]

    # ── Lloyd iterations ─────────────────────────────────────────────────────
    labels = np.zeros(n, dtype=np.int32)
    for _ in range(max_iter):
        dists = np.linalg.norm(data[:, None] - centers[None], axis=2)
        new_labels = np.argmin(dists, axis=1).astype(np.int32)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for c in range(k):
            mask = labels == c
            if mask.any():
                centers[c] = data[mask].mean(axis=0)
    return labels


def dominant_colors_kmeans(
    pixels: np.ndarray,
    k: int = 2,
    max_pixels: int = 4000,
) -> tuple[list[tuple[int, int, int]], list[float], np.ndarray]:
    """
    Tìm k màu trội từ mảng pixel RGB (N×3) bằng K-means trong không gian Lab.
    Dùng scikit-learn nếu có; fallback numpy nếu không.
    Trả về: (colors[(R,G,B)], weights[0..1], labels[N]).
    """
    if len(pixels) == 0:
        return [], [], np.array([], dtype=np.int32)

    if len(pixels) > max_pixels:
        idx = np.random.choice(len(pixels), max_pixels, replace=False)
        sample = pixels[idx]
    else:
        sample = pixels

    lab_sample = rgb_to_lab(sample)
    k_actual = min(k, len(sample))

    try:
        from sklearn.cluster import KMeans       # type: ignore[import]
        from sklearn.metrics import pairwise_distances  # type: ignore[import]
        km = KMeans(n_clusters=k_actual, n_init=10, random_state=42)
        km.fit(lab_sample)
        lab_all = rgb_to_lab(pixels)
        dists = pairwise_distances(lab_all, km.cluster_centers_)
        labels = np.argmin(dists, axis=1).astype(np.int32)
    except ImportError:
        # fallback: K-means thuần numpy (chậm hơn ~3×, đủ cho ảnh UI)
        lab_all = rgb_to_lab(pixels)
        labels = _kmeans_numpy(lab_all, k_actual)

    colors: list[tuple[int, int, int]] = []
    weights: list[float] = []
    total = len(pixels)
    for c_idx in range(k_actual):
        mask = labels == c_idx
        count = int(mask.sum())
        if count == 0:
            continue
        mean_rgb = pixels[mask].mean(axis=0).astype(int)
        colors.append((int(mean_rgb[0]), int(mean_rgb[1]), int(mean_rgb[2])))
        weights.append(count / total)

    return colors, weights, labels
