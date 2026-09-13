import numpy as np
from PIL import Image
from scipy.stats import chisquare
import time


# --- Brute Force Seed Recovery ---

def prng_share1_from_seed(seed: int, shape: tuple) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=shape, dtype=np.uint8)


def brute_force_attack(share2: Image.Image, original: Image.Image,
                        true_seed: int, seed_range: int = 100000,
                        progress_callback=None, preview_frames: int = 50):
    """
    Simulate an attacker who intercepts Share 2 and attempts to recover
    the secret image by brute-forcing seeds in [0, seed_range).

    Only materializes a full candidate image (an (H, W) array generation +
    XOR) for preview frames and the final matching attempt -- every other
    attempt is a cheap integer comparison. This matters once seed_range and
    image resolution both get large: doing full array work on every single
    attempt would be O(seed_range * H * W) and can take a very long time in
    a UI loop.

    Parameters
    ----------
    share2            : intercepted share
    original          : secret image (used only to verify success)
    true_seed         : the actual seed used during PRNG generation
    seed_range        : number of seeds attacker tries, [0, seed_range)
    progress_callback : optional callable(attempt, total, recovered_img_or_None)
    preview_frames    : roughly how many preview updates to emit across the
                         whole search (keeps the UI responsive at large ranges)

    Returns
    -------
    dict with keys: success, attempts, time_taken, recovered
    """
    s2 = np.array(share2.convert('L'), dtype=np.uint8)
    H, W = s2.shape

    start = time.time()
    preview_stride = max(1, seed_range // max(1, preview_frames))

    for attempt in range(seed_range):
        is_match = (attempt == true_seed)
        is_preview = progress_callback and (attempt % preview_stride == 0)

        if is_match or is_preview:
            candidate_s1 = prng_share1_from_seed(attempt, (H, W))
            candidate_img = np.bitwise_xor(candidate_s1, s2)

            if progress_callback:
                progress_callback(attempt, seed_range, Image.fromarray(candidate_img))

            if is_match:
                elapsed = time.time() - start
                return {
                    "success": True,
                    "attempts": attempt + 1,
                    "time_taken": round(elapsed, 3),
                    "recovered": Image.fromarray(candidate_img)
                }
        elif progress_callback and attempt % max(1, seed_range // 200) == 0:
            # Cheap progress-bar-only update (no image work) between preview frames
            progress_callback(attempt, seed_range, None)

    elapsed = time.time() - start
    return {
        "success": False,
        "attempts": seed_range,
        "time_taken": round(elapsed, 3),
        "recovered": None
    }


# --- Replay Attack ---

def replay_attack(image: Image.Image, generate_fn, use_qrng: bool):
    """
    Generate shares twice from the same image, simulating two "sessions".

    PRNG: session 2 explicitly reuses session 1's seed -- this is what a
    replay attack actually looks like (the attacker replays/reuses material
    from a session where randomness got reused), not a fresh random draw
    that happens to coincide. Result: identical shares, attack succeeds.

    QRNG: each call draws fresh quantum measurements, no seed exists to
    reuse. Result: different shares every time, attack fails.

    Returns
    -------
    dict with keys: shares_identical, share1_run1, share1_run2, diff_image,
    seed_run1, seed_run2
    """
    s1_a, s2_a, seed_a = generate_fn(image, use_qrng=use_qrng)

    if use_qrng:
        s1_b, s2_b, seed_b = generate_fn(image, use_qrng=use_qrng)
    else:
        # The attacker reuses session 1's seed -- this IS the replay attack.
        s1_b, s2_b, seed_b = generate_fn(image, use_qrng=use_qrng, seed=seed_a)

    arr_a = np.array(s1_a.convert('L'), dtype=np.uint8)
    arr_b = np.array(s1_b.convert('L'), dtype=np.uint8)

    identical = np.array_equal(arr_a, arr_b)
    diff = np.abs(arr_a.astype(int) - arr_b.astype(int)).astype(np.uint8)
    diff_image = Image.fromarray(diff)

    return {
        "shares_identical": identical,
        "share1_run1": s1_a,
        "share1_run2": s1_b,
        "diff_image": diff_image,
        "seed_run1": seed_a,
        "seed_run2": seed_b
    }


# --- Statistical Analysis ---

def shannon_entropy(arr: np.ndarray) -> float:
    """Compute Shannon entropy of a grayscale image array in bits per pixel."""
    flat = arr.flatten()
    counts = np.bincount(flat, minlength=256).astype(float)
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def chi_square_uniformity(arr: np.ndarray):
    """
    Chi-square test for uniformity of pixel value distribution.
    A truly random share should have roughly equal frequency across all 256 values.

    Returns
    -------
    statistic : float
    p_value   : float  (high p -> more uniform -> more random)
    """
    flat = arr.flatten()
    observed = np.bincount(flat, minlength=256).astype(float)
    expected = np.full(256, flat.size / 256)
    stat, p = chisquare(observed, f_exp=expected)
    return float(stat), float(p)


def analyze_share(share: Image.Image) -> dict:
    """
    Run full statistical analysis on a share image.

    Returns
    -------
    dict with entropy, chi_square_stat, chi_square_p, histogram
    """
    arr = np.array(share.convert('L'), dtype=np.uint8)
    entropy = shannon_entropy(arr)
    chi_stat, chi_p = chi_square_uniformity(arr)
    histogram = np.bincount(arr.flatten(), minlength=256)

    return {
        "entropy": round(entropy, 4),
        "chi_square_stat": round(chi_stat, 2),
        "chi_square_p": round(chi_p, 6),
        "histogram": histogram,
        "max_entropy": 8.0
    }
