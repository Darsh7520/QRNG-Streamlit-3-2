import streamlit as st
from PIL import Image
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from naor_shamir import generate_ns_shares, combine_ns_shares


def render():
    st.title("🧩 Naor-Shamir (2,2) Visual Cryptography")
    st.markdown("""
    Upload a secret image and generate two shares using Naor-Shamir basis permutation.
    Each pixel expands to a **4×4 subpixel block** resulting in shares 4× larger in each dimension.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded = st.file_uploader("Upload secret image", type=["png", "jpg", "jpeg", "bmp"])
        mode = st.radio("Randomness source", ["QRNG (Quantum)", "PRNG (Classical)"])
        use_qrng = mode == "QRNG (Quantum)"

        st.caption("Recommended: use a small image (64×64 or 128×128) as Naor-Shamir is pixel-by-pixel and may take time on large images.")

        if uploaded:
            image = Image.open(uploaded)
            st.image(image, caption=f"Secret Image ({image.width}×{image.height})", use_container_width=True)

    with col2:
        if uploaded and st.button("Generate Shares", type="primary"):
            image = Image.open(uploaded)

            with st.spinner("Generating Naor-Shamir shares... this may take a moment."):
                share1, share2, seed = generate_ns_shares(image, use_qrng=use_qrng)

            st.session_state["ns_share1"] = share1
            st.session_state["ns_share2"] = share2
            st.session_state["ns_original"] = image
            st.session_state["ns_seed"] = seed
            st.session_state["ns_mode"] = "QRNG" if use_qrng else "PRNG"

            W, H = image.width, image.height
            if not use_qrng:
                st.info(f"PRNG Seed used: `{seed}`")
            else:
                st.success("Shares generated using true quantum randomness.")

            st.caption(f"Share dimensions: {W*4}×{H*4} px (4× pixel expansion)")

    if "ns_share1" in st.session_state:
        st.divider()
        st.subheader("Generated Shares")
        c1, c2 = st.columns(2)
        with c1:
            st.image(st.session_state["ns_share1"], caption="Share 1", use_container_width=True)
        with c2:
            st.image(st.session_state["ns_share2"], caption="Share 2", use_container_width=True)

        st.divider()
        st.subheader("Reconstruction")
        if st.button("Stack Shares → Reconstruct"):
            recovered = combine_ns_shares(
                st.session_state["ns_share1"],
                st.session_state["ns_share2"]
            )
            st.image(recovered, caption="Reconstructed via OR stacking", use_container_width=True)
            st.info("Naor-Shamir reconstruction is perceptual not lossless. Black pixels appear dark grey after stacking.")
