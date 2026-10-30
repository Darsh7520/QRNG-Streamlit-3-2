# -*- coding: utf-8 -*-
"""
Quantum-driven probabilistic visual cryptography
OR-based recovery (matches physical transparency stacking).

Two recovery paths are provided:
  - recover_or_exact / the printed share bits: single bit per pixel per share,
    what you'd actually print and physically stack.
  - recover_or_continuous: a per-pixel probability estimate built from the
    FULL shot statistics of each pixel (not just the majority-vote bit),
    which avoids blurring across true image edges the way spatial smoothing
    of a single noisy bit-per-pixel does.

Requirements: qiskit, qiskit-aer, numpy, pillow, scipy
"""

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import math

BACKEND = AerSimulator(method='matrix_product_state')


def run_circuit_batch(theta, n_pixels, shots_per_pixel=300, pairs_per_batch=256):
    """
    Run batches of independent 2-qubit pairs.

    Returns:
      bits_A, bits_B : one representative bit per pixel per share (majority
                        vote across shots) -- use these for the printable
                        share images.
      p_or           : per-pixel estimate of P(A OR B = 1), computed from
                        ALL shots for that pixel, not just the majority bit.
                        This is what removes the need for heavy spatial
                        smoothing in recovery.
    """
    bits_A, bits_B, p_or = [], [], []
    while len(bits_A) < n_pixels:
        n_pairs = min(pairs_per_batch, n_pixels - len(bits_A))
        n_qubits = n_pairs * 2
        qc = QuantumCircuit(n_qubits, n_qubits)
        for k in range(n_pairs):
            q0, q1 = k * 2, k * 2 + 1
            qc.h(q0)
            qc.cx(q0, q1)
            if theta != 0:
                qc.ry(theta, q1)
        qc.measure(range(n_qubits), range(n_qubits))
        job = BACKEND.run(qc, shots=shots_per_pixel, memory=True)
        res = job.result()
        mem = res.get_memory(qc)
        shots_bits = np.array([[int(b) for b in bs] for bs in mem], dtype=np.uint8)
        for pair_idx in range(n_pairs):
            ia, ib = pair_idx * 2, pair_idx * 2 + 1
            a_votes = shots_bits[:, ia]
            b_votes = shots_bits[:, ib]
            or_votes = np.logical_or(a_votes, b_votes)
            bits_A.append(1 if a_votes.sum() >= (shots_per_pixel / 2.0) else 0)
            bits_B.append(1 if b_votes.sum() >= (shots_per_pixel / 2.0) else 0)
            p_or.append(float(or_votes.mean()))
    return (np.array(bits_A[:n_pixels], dtype=np.uint8),
            np.array(bits_B[:n_pixels], dtype=np.uint8),
            np.array(p_or[:n_pixels], dtype=np.float32))


def generate_quantum_correlated_shares(image_path, mode='binary',
                                        shots_per_pixel=300, quant_levels=32):
    """
    Returns: share1_bits, share2_bits (printable, 1=black), p_or_map
    (per-pixel P(OR=1) estimate, same shape as image), secret_array
    """
    if mode == 'binary':
        img = Image.open(image_path).convert('1')
        arr = np.array(img, dtype=np.uint8)
        secret = 1 - arr
    else:
        img = Image.open(image_path).convert('L')
        arr = np.array(img, dtype=np.float32) / 255.0
        secret = arr

    H, W = secret.shape[:2]
    share1 = np.zeros((H, W), dtype=np.uint8)
    share2 = np.zeros((H, W), dtype=np.uint8)
    p_or_map = np.zeros((H, W), dtype=np.float32)

    if mode == 'binary':
        black_mask = (secret == 1)
        white_mask = (secret == 0)
        n_black = int(black_mask.sum())
        n_white = int(white_mask.sum())
        if n_black > 0:
            A, B, P = run_circuit_batch(theta=0.0, n_pixels=n_black, shots_per_pixel=shots_per_pixel)
            share1[black_mask] = A
            share2[black_mask] = B
            p_or_map[black_mask] = P
        if n_white > 0:
            A, B, P = run_circuit_batch(theta=math.pi / 2.0, n_pixels=n_white, shots_per_pixel=shots_per_pixel)
            share1[white_mask] = A
            share2[white_mask] = B
            p_or_map[white_mask] = P
    else:
        levels = max(2, int(quant_levels))
        quant = np.clip((secret * (levels - 1)).astype(int), 0, levels - 1)
        for level in range(levels):
            mask = (quant == level)
            n = int(mask.sum())
            if n == 0:
                continue
            g = level / (levels - 1)
            theta = (math.pi / 2.0) * g
            A, B, P = run_circuit_batch(theta=theta, n_pixels=n, shots_per_pixel=shots_per_pixel)
            share1[mask] = A
            share2[mask] = B
            p_or_map[mask] = P

    return share1, share2, p_or_map, secret


def save_shares(share_bits, filename):
    img = Image.fromarray((1 - share_bits) * 255).convert('L')
    img.save(filename)


def recover_or_exact(share1_bits, share2_bits):
    """
    Literal physical result of stacking the two printed shares. No
    per-pixel statistics involved -- this is what you'd actually see if you
    printed both shares and laid one on top of the other. Expect this to
    look mostly like noise; a single stacked pixel carries almost no
    information on its own.
    """
    stacked = np.logical_or(share1_bits == 1, share2_bits == 1).astype(np.uint8)
    img = Image.fromarray((1 - stacked) * 255).convert('L')
    return img, stacked


def recover_or_continuous(p_or_map, denoise_sigma=0.5, secret=None,
                           contrast_stretch=True, use_threshold=False, threshold_g=0.5):
    """
    Digital/statistical reconstruction using the per-pixel P(OR=1) estimate
    (built from each pixel's own shots -- see run_circuit_batch), not from
    spatially smoothing the printed share bits. denoise_sigma should now be
    small (0.3-0.8): it's only mopping up residual shot noise, not doing the
    heavy lifting of estimating the signal, so it no longer blurs across
    true image edges the way the old approach did.

    theory: P(OR=1) = 1 - cos^2(theta/2)/2  ->  0.5 for black, 0.75 for white
    """
    p = np.clip(p_or_map, 0.5, 1.0)
    if denoise_sigma > 0:
        p = gaussian_filter(p, sigma=denoise_sigma)
        p = np.clip(p, 0.5, 1.0)

    if secret is not None:
        try:
            if secret.dtype == np.uint8 or secret.dtype == np.int64:
                black_mask = (secret == 1)
                white_mask = (secret == 0)
            else:
                black_mask = (secret >= 0.5)
                white_mask = (secret < 0.5)
            mean_b = float(p[black_mask].mean()) if black_mask.sum() > 0 else float('nan')
            mean_w = float(p[white_mask].mean()) if white_mask.sum() > 0 else float('nan')
            print(f"P(OR=1): black mean={mean_b:.4f}  white mean={mean_w:.4f}  (theory: 0.50 / 0.75)")
        except Exception as e:
            print("Diagnostics error:", e)

    inner = np.clip(2.0 * (1.0 - p), 0.0, 1.0)
    g = (4.0 / math.pi) * np.arccos(np.sqrt(inner))
    g = np.clip(g, 0.0, 1.0)

    if contrast_stretch:
        g_min, g_max = float(g.min()), float(g.max())
        if g_max - g_min > 1e-6:
            g = (g - g_min) / (g_max - g_min)

    gray_img = (g * 255.0).astype(np.uint8)
    recovered_gray = Image.fromarray(gray_img).convert('L')

    recovered_binary = None
    if use_threshold:
        binary = np.where(g > threshold_g, 255, 0).astype(np.uint8)
        recovered_binary = Image.fromarray(binary).convert('L')

    return recovered_gray, recovered_binary, p


def verify_stats_from_shares(share1_bits, share2_bits, secret=None):
    b1 = (share1_bits == 1).astype(np.uint8)
    b2 = (share2_bits == 1).astype(np.uint8)
    or_stack = (b1 | b2)
    print("Overall P(OR=1) [printed shares only]:", float(or_stack.mean()))
    if secret is not None:
        try:
            if secret.dtype == np.uint8 or secret.dtype == np.int64:
                black_mask = (secret == 1)
                white_mask = (secret == 0)
            else:
                black_mask = (secret >= 0.5)
                white_mask = (secret < 0.5)
            print("  Black pixel P(OR=1):", float(or_stack[black_mask].mean()))
            print("  White pixel P(OR=1):", float(or_stack[white_mask].mean()))
        except Exception as e:
            print("Verification error:", e)


def main():
    image_path = input("Secret image path: ").strip()
    mode = input("Mode 'binary' or 'greyscale' [binary]: ").strip() or 'binary'
    shots = int(input("shots per pixel [300]: ").strip() or 300)
    denoise_sigma = float(input("Residual denoise sigma [0.5]: ").strip() or 0.5)
    quant_levels = int(input("Greyscale quant levels [32]: ").strip() or 32)

    share1, share2, p_or_map, secret = generate_quantum_correlated_shares(
        image_path, mode=mode, shots_per_pixel=shots, quant_levels=quant_levels)

    save_shares(share1, "qc_share_1.png")
    save_shares(share2, "qc_share_2.png")
    print("Saved qc_share_1.png and qc_share_2.png (single-bit-per-pixel, printable)")

    verify_stats_from_shares(share1, share2, secret=secret)

    exact_img, _ = recover_or_exact(share1, share2)
    exact_img.save("qc_recovered_or_exact.png")
    print("Saved qc_recovered_or_exact.png (literal physical stack -- expect noise)")

    recovered_gray, recovered_binary, p = recover_or_continuous(
        p_or_map, denoise_sigma=denoise_sigma, secret=secret,
        contrast_stretch=True, use_threshold=True, threshold_g=0.5)

    recovered_gray.save("qc_recovered_or_continuous.png")
    if recovered_binary is not None:
        recovered_binary.save("qc_recovered_or_binary.png")
    print("Saved qc_recovered_or_continuous.png and qc_recovered_or_binary.png")
    print("If still soft: raise shots_per_pixel (500-1000) rather than denoise_sigma -- "
          "sharpness now scales with per-pixel shot count, not smoothing radius.")


if __name__ == "__main__":
    main()