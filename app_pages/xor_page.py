import streamlit as st
from PIL import Image
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xor_vc import generate_xor_shares, combine_xor_shares


def render():
    st.title("🔑 XOR-Based Visual Cryptography")
    st.markdown("Upload a secret image and generate two shares using either QRNG or PRNG.")

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded = st.file_uploader("Upload secret image", type=["png", "jpg", "jpeg", "bmp"])
        mode = st.radio("Randomness source", ["QRNG (Quantum)", "PRNG (Classical)"])
        use_qrng = mode == "QRNG (Quantum)"

        if uploaded:
            image = Image.open(uploaded)
            st.image(image, caption="Secret Image", use_container_width=True)

    with col2:
        if uploaded and st.button("Generate Shares", type="primary"):
            image = Image.open(uploaded)

            with st.spinner("Generating shares..." if use_qrng else "Generating shares with PRNG..."):
                share1, share2, seed = generate_xor_shares(image, use_qrng=use_qrng)

            st.session_state["xor_share1"] = share1
            st.session_state["xor_share2"] = share2
            st.session_state["xor_original"] = image
            st.session_state["xor_seed"] = seed
            st.session_state["xor_mode"] = "QRNG" if use_qrng else "PRNG"

            if not use_qrng:
                st.info(f"PRNG Seed used: `{seed}` — an attacker who finds this seed can reconstruct the image.")
            else:
                st.success("Shares generated using true quantum randomness. No seed exists.")

    if "xor_share1" in st.session_state:
        st.divider()
        st.subheader("Generated Shares")
        c1, c2 = st.columns(2)
        with c1:
            st.image(st.session_state["xor_share1"], caption="Share 1", use_container_width=True)
        with c2:
            st.image(st.session_state["xor_share2"], caption="Share 2", use_container_width=True)

        st.divider()
        st.subheader("Reconstruction")
        if st.button("Combine Shares → Reconstruct"):
            recovered = combine_xor_shares(
                st.session_state["xor_share1"],
                st.session_state["xor_share2"]
            )
            st.image(recovered, caption="Reconstructed Image", use_container_width=True)
            st.success("Lossless reconstruction complete.")
