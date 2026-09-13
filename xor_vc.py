import numpy as np
from PIL import Image
from qrng import qrng_batch


def generate_xor_shares(image: Image.Image, use_qrng: bool = True, seed: int = None):
    """
    Generate two XOR-based shares from a secret image.

    Parameters
    ----------
    image    : PIL.Image -- secret image (any mode, converted to grayscale)
    use_qrng : bool -- if True use QRNG else use numpy PRNG
    seed     : int or None -- only used when use_qrng=False. If provided, the
               PRNG is seeded with this exact value instead of picking a new
               random one. This is how a replay attack is simulated: the
               attacker doesn't guess a seed, they reuse one that was already
               generated in a prior "session".

    Returns
    -------
    share1, share2 : PIL.Image (grayscale)
    seed           : int or None -- the seed actually used, if PRNG mode
    """
    img_arr = np.array(image.convert('L'), dtype=np.uint8)
    H, W = img_arr.shape

    if use_qrng:
        seed = None
        flat_bits = qrng_batch(H * W * 8)
        random_matrix = flat_bits.reshape(H, W, 8)
        share1_arr = np.packbits(random_matrix, axis=-1).reshape(H, W)
    else:
        if seed is None:
            seed = int(np.random.randint(0, 100000))
        rng = np.random.default_rng(seed)
        share1_arr = rng.integers(0, 256, size=(H, W), dtype=np.uint8)

    share2_arr = np.bitwise_xor(img_arr, share1_arr)

    share1 = Image.fromarray(share1_arr)
    share2 = Image.fromarray(share2_arr)
    return share1, share2, seed


def combine_xor_shares(share1: Image.Image, share2: Image.Image) -> Image.Image:
    """
    Reconstruct secret image by XOR-ing two shares.
    """
    s1 = np.array(share1.convert('L'), dtype=np.uint8)
    s2 = np.array(share2.convert('L'), dtype=np.uint8)
    recovered = np.bitwise_xor(s1, s2)
    return Image.fromarray(recovered)
