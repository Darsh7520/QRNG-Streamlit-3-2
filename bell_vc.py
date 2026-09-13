"""
Bell-pair entangled visual cryptography.

Unlike xor_vc.py (uses a QRNG/PRNG bitstream, XOR reconstruction, no expansion)
and naor_shamir.py (uses a QRNG/PRNG permutation choice, OR-stack reconstruction,
4x pixel expansion), this module generates the two shares directly from
entangled Bell pairs: share bits aren't drawn from a random stream at all,
they're the two halves of a single measured quantum state.

theta=0   -> secret pixel is black -> qubits strongly correlated (P(A=B)=1)
theta=pi/2 -> secret pixel is white -> qubits decorrelated (P(A=B)=0.5)

Reconstruction is OR-based (physical stacking), same as Naor-Shamir. Because
each individual share bit's own outcome is exactly 50/50 no matter what theta
is (only the *joint* correlation carries the secret), a single physical stack
is noisy. A clean image needs the full multi-shot statistics per pixel --
see combine_bell_shares_statistical.
"""

import math
import numpy as np
from PIL import Image
from qiskit import QuantumCircuit
from qiskit_aer import Aer

_BACKEND = Aer.get_backend('qasm_simulator')
_PAIRS_PER_BATCH = 128  # 256 qubits per circuit, matching qrng.py's batch size


def _run_entangled_batch(theta: float, n_pairs: int, shots_per_pixel: int = 1):
    """
    Run n_pairs independent Bell pairs (qubit B additionally rotated by theta).

    Returns
    -------
    bits_A, bits_B : majority-vote bit per pair -- used for the printable share
    p_or           : per-pair P(A OR B = 1) estimated from ALL shots, not just
                      the majority-vote bit -- used for statistical reconstruction
    """
    bits_A, bits_B, p_or = [], [], []
    remaining = n_pairs
    while remaining > 0:
        n = min(_PAIRS_PER_BATCH, remaining)
        qc = QuantumCircuit(n * 2, n * 2)
        for k in range(n):
            q0, q1 = k * 2, k * 2 + 1
            qc.h(q0)
            qc.cx(q0, q1)
            if theta != 0:
                qc.ry(theta, q1)
        qc.measure(range(n * 2), range(n * 2))
        job = _BACKEND.run(qc, shots=shots_per_pixel, memory=True)
        mem = job.result().get_memory(qc)
        shots_bits = np.array([[int(b) for b in bs] for bs in mem], dtype=np.uint8)
        for k in range(n):
            ia, ib = k * 2, k * 2 + 1
            a_votes = shots_bits[:, ia]
            b_votes = shots_bits[:, ib]
            or_votes = np.logical_or(a_votes, b_votes)
            bits_A.append(1 if a_votes.sum() >= (shots_per_pixel / 2.0) else 0)
            bits_B.append(1 if b_votes.sum() >= (shots_per_pixel / 2.0) else 0)
            p_or.append(float(or_votes.mean()))
        remaining -= n
    return (np.array(bits_A, dtype=np.uint8),
            np.array(bits_B, dtype=np.uint8),
            np.array(p_or, dtype=np.float32))


def generate_bell_shares(image: Image.Image, shots_per_pixel: int = 1):
    """
    Generate two OR-stackable shares from a binary secret image using
    entangled Bell pairs. No pixel expansion (unlike Naor-Shamir's 4x).

    Returns
    -------
    share1, share2 : PIL.Image (grayscale, same size as input, printable)
    p_or_map       : np.ndarray -- per-pixel P(A OR B=1) from shot statistics
    secret_arr     : np.ndarray -- 1=black/0=white, for diagnostics
    """
    img = image.convert('1')
    secret = 1 - np.array(img, dtype=np.uint8)
    H, W = secret.shape

    black_mask = (secret == 1)
    white_mask = (secret == 0)
    n_black = int(black_mask.sum())
    n_white = int(white_mask.sum())

    share1 = np.zeros((H, W), dtype=np.uint8)
    share2 = np.zeros((H, W), dtype=np.uint8)
    p_or_map = np.zeros((H, W), dtype=np.float32)

    if n_black > 0:
        A, B, P = _run_entangled_batch(0.0, n_black, shots_per_pixel)
        share1[black_mask] = A
        share2[black_mask] = B
        p_or_map[black_mask] = P
    if n_white > 0:
        A, B, P = _run_entangled_batch(math.pi / 2.0, n_white, shots_per_pixel)
        share1[white_mask] = A
        share2[white_mask] = B
        p_or_map[white_mask] = P

    img1 = Image.fromarray((1 - share1) * 255).convert('L')
    img2 = Image.fromarray((1 - share2) * 255).convert('L')
    return img1, img2, p_or_map, secret


def combine_bell_shares_exact(share1: Image.Image, share2: Image.Image) -> Image.Image:
    """Literal physical stacking result -- overlaying the two printed shares."""
    s1 = np.array(share1.convert('L'), dtype=np.uint8)
    s2 = np.array(share2.convert('L'), dtype=np.uint8)
    is_black_1 = (s1 < 128).astype(np.uint8)
    is_black_2 = (s2 < 128).astype(np.uint8)
    stacked = np.logical_or(is_black_1, is_black_2).astype(np.uint8)
    return Image.fromarray((1 - stacked) * 255).convert('L')


def combine_bell_shares_statistical(p_or_map: np.ndarray, denoise_sigma: float = 0.5) -> Image.Image:
    """
    Cleaner reconstruction from per-pixel shot statistics rather than one
    physical stack. Inverts the theoretical relationship
    P(OR=1) = 1 - cos^2(theta/2)/2  (0.5 for black, 0.75 for white).
    """
    from scipy.ndimage import gaussian_filter
    p = np.clip(p_or_map, 0.5, 1.0)
    if denoise_sigma > 0:
        p = np.clip(gaussian_filter(p, sigma=denoise_sigma), 0.5, 1.0)
    inner = np.clip(2.0 * (1.0 - p), 0.0, 1.0)
    g = (4.0 / math.pi) * np.arccos(np.sqrt(inner))
    g = np.clip(g, 0.0, 1.0)
    g_min, g_max = float(g.min()), float(g.max())
    if g_max - g_min > 1e-6:
        g = (g - g_min) / (g_max - g_min)
    gray = (g * 255.0).astype(np.uint8)
    return Image.fromarray(gray).convert('L')


def correlation_test(n_bits: int, shots_per_pixel: int = 1):
    """
    Direct entanglement demonstration: generate n_bits of maximally-correlated
    Bell-pair bits (theta=0) and return the fraction where A==B, plus the raw
    bit arrays.
    """
    A, B, _ = _run_entangled_batch(0.0, n_bits, shots_per_pixel)
    agreement = float((A == B).mean())
    return agreement, A, B
