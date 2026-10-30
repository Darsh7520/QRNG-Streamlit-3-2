import hashlib
from io import BytesIO
import os
import sys

import numpy as np
from PIL import Image, UnidentifiedImageError
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_pages.image_downloads import show_image
from entanglement import (
    generate_quantum_correlated_shares,
    recover_or_continuous,
    recover_or_exact,
)


def _show_output(image, caption, filename):
    show_image(image, caption=caption, filename=filename, width="stretch")


def render():
    st.title("Bell-Pair Entangled Visual Cryptography")
    st.markdown("""
    Generate quantum-correlated shares using the implementation in
    `entanglement.py`, with one pixel per share for each secret pixel.
    View both printable shares and all three OR-based reconstructions below.
    The quantum circuits run locally using Qiskit's Aer simulator.
    """)
    uploaded = st.file_uploader(
        "Upload a secret image", type=["png", "jpg", "jpeg", "bmp"]
    )
    if uploaded is None:
        st.session_state.pop("bell_entanglement_result", None)
        return

    image_bytes = uploaded.getvalue()
    source_id = hashlib.sha256(image_bytes).hexdigest()
    result = st.session_state.get("bell_entanglement_result")
    if result is not None and result["source_id"] != source_id:
        st.session_state.pop("bell_entanglement_result", None)

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = source.copy()
    except (UnidentifiedImageError, OSError, ValueError):
        st.error("This file could not be opened as an image. Please upload another image.")
        return

    show_image(
        image, caption=f"Secret image ({image.width} x {image.height})",
        width="stretch", filename='bell_secret.png')
    st.caption(
        "Small images (32 x 32 to 64 x 64) are recommended for faster simulation. "
        "The uploaded resolution is preserved."
    )
    with st.form("bell_entanglement_settings"):
        c1, c2 = st.columns(2)
        with c1:
            mode = st.selectbox("Mode", ["binary", "greyscale"])
            shots = st.slider("Shots per pixel", 1, 1000, 300)
        with c2:
            denoise_sigma = st.slider(
                "Residual denoise sigma", 0.0, 2.0, 0.5, step=0.1,
                help="Small values reduce shot noise while retaining image edges.",
            )
            quant_levels = st.slider(
                "Grayscale quantization levels", 2, 64, 32,
                help="Used only in greyscale mode.",
            )
        generate = st.form_submit_button("Generate Entangled Shares", type="primary")

    if generate:
        with st.spinner("Generating quantum-correlated shares and reconstructions..."):
            share1, share2, p_or_map, secret = generate_quantum_correlated_shares(
                BytesIO(image_bytes), mode=mode,
                shots_per_pixel=shots, quant_levels=quant_levels,
            )
            exact, _ = recover_or_exact(share1, share2)
            continuous, binary, _ = recover_or_continuous(
                p_or_map, denoise_sigma=denoise_sigma,
                contrast_stretch=True, use_threshold=True, threshold_g=0.5,
            )
            # Binary secrets use 1=black; grayscale secrets store brightness.
            processed = (1 - secret) * 255 if mode == "binary" else secret * 255
            st.session_state["bell_entanglement_result"] = {
                "source_id": source_id,
                "settings": f"{mode}, {shots} shots/pixel, denoise sigma {denoise_sigma}"
                + (f", {quant_levels} grayscale levels" if mode == "greyscale" else ""),
                "secret": Image.fromarray(processed.astype(np.uint8)).convert("L"),
                "share1": Image.fromarray((1 - share1) * 255).convert("L"),
                "share2": Image.fromarray((1 - share2) * 255).convert("L"),
                "exact": exact,
                "continuous": continuous,
                "binary": binary,
            }
        st.success("Both shares and all three reconstructions are ready.")

    result = st.session_state.get("bell_entanglement_result")
    if result is None:
        return
    st.caption(f"Displayed results: {result['settings']}")
    show_image(result["secret"], caption="Processed secret", width="stretch", filename='bell_processed_secret.png')
    st.divider()
    st.subheader("Generated Shares")
    c1, c2 = st.columns(2)
    with c1:
        _show_output(result["share1"], "Share 1", "qc_share_1.png")
    with c2:
        _show_output(result["share2"], "Share 2", "qc_share_2.png")

    st.divider()
    st.subheader("Reconstruction")
    st.caption(
        "The physical stack uses the printed share bits and can look noisy. "
        "Continuous and binary reconstructions use the full per-pixel shot statistics."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        _show_output(result["exact"], "Physical OR stack", "qc_recovered_or_exact.png")
    with c2:
        _show_output(
            result["continuous"], "Continuous reconstruction", "qc_recovered_or_continuous.png"
        )
    with c3:
        _show_output(result["binary"], "Binary reconstruction", "qc_recovered_or_binary.png")
