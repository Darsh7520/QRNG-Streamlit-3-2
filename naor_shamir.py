import numpy as np
from PIL import Image
from itertools import permutations
from qrng import qrng_batch

ALL_PERMS = list(permutations(range(4)))

S0 = np.array([[1, 1, 0, 0],
               [0, 0, 1, 1]], dtype=np.uint8)

S1 = np.array([[1, 1, 0, 0],
               [1, 1, 0, 0]], dtype=np.uint8)


def apply_permutation(matrix, perm):
    return matrix[:, list(perm)]


def generate_ns_shares(image: Image.Image, use_qrng: bool = True):
    """
    Generate Naor-Shamir (2,2) shares with 4x pixel expansion.

    Parameters
    ----------
    image    : PIL.Image
    use_qrng : bool

    Returns
    -------
    share1, share2 : PIL.Image (grayscale, 4x expanded)
    seed           : int or None
    """
    img = image.convert('1')
    image_arr = 1 - np.array(img, dtype=np.uint8)
    H, W = image_arr.shape
    seed = None

    if use_qrng:
        flat_bits = qrng_batch(H * W * 5)
        get_perm_idx = lambda bit_idx: (
            int(''.join(str(b) for b in flat_bits[bit_idx:bit_idx+5]), 2) % 24,
            bit_idx + 5
        )
    else:
        seed = np.random.randint(0, 100000)
        rng = np.random.default_rng(seed)
        prng_indices = rng.integers(0, 24, size=(H * W,))
        counter = [0]
        def get_perm_idx(bit_idx):
            idx = prng_indices[counter[0]]
            counter[0] += 1
            return idx, bit_idx

    share1 = np.zeros((H * 4, W * 4), dtype=np.uint8)
    share2 = np.zeros((H * 4, W * 4), dtype=np.uint8)

    bit_idx = 0
    for i in range(H):
        for j in range(W):
            pixel = image_arr[i, j]
            perm_idx, bit_idx = get_perm_idx(bit_idx)
            basis = apply_permutation(S0 if pixel == 0 else S1, ALL_PERMS[perm_idx])
            share1[i*4:(i+1)*4, j*4:(j+1)*4] = np.tile(basis[0], (4, 1))
            share2[i*4:(i+1)*4, j*4:(j+1)*4] = np.tile(basis[1], (4, 1))

    img1 = Image.fromarray((1 - share1) * 255)
    img2 = Image.fromarray((1 - share2) * 255)
    return img1, img2, seed


def combine_ns_shares(share1: Image.Image, share2: Image.Image) -> Image.Image:
    """
    Reconstruct via OR stacking simulating physical transparency overlay.
    """
    s1 = np.array(share1.convert('L'), dtype=np.uint8)
    s2 = np.array(share2.convert('L'), dtype=np.uint8)
    is_black_1 = (s1 < 128).astype(np.uint8)
    is_black_2 = (s2 < 128).astype(np.uint8)
    stacked = np.logical_or(is_black_1, is_black_2).astype(np.uint8)
    return Image.fromarray(stacked * 255)
