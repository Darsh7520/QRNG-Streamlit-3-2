import streamlit as st
from PIL import Image
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xor_vc import generate_xor_shares
from attacks import replay_attack


def render():
    st.title(" Replay Attack Demonstration")
    st.markdown("""
    A replay attack occurs when an adversary intercepts shares from a previous session
    and reuses them (or the randomness behind them) in a future session to reconstruct
    the secret image.

    - **PRNG mode**: Session 2 reuses session 1's seed → identical shares → replay succeeds.
    - **QRNG mode**: Each session draws fresh quantum measurements, no seed exists to reuse → replay fails completely.
    """)

    st.divider()

    uploaded = st.file_uploader("Upload a secret image", type=["png", "jpg", "jpeg", "bmp"])

    if not uploaded:
        st.info("Upload an image to begin the demonstration.")
        return

    image = Image.open(uploaded).convert('L')
    st.image(image, caption=f"Secret Image ({image.width}×{image.height})", width=200)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⚠️ PRNG — Replay Succeeds")
        st.markdown("Session 2 reuses session 1's seed. Both sessions produce identical Share 1.")

        if st.button("Run PRNG Replay Test", type="primary"):
            with st.spinner("Generating session 1, then replaying its seed into session 2..."):
                result = replay_attack(image, generate_xor_shares, use_qrng=False)

            c1, c2 = st.columns(2)
            with c1:
                st.image(result["share1_run1"], caption=f"Session 1 Share 1\nSeed: {result['seed_run1']}", use_container_width=True)
            with c2:
                st.image(result["share1_run2"], caption=f"Session 2 Share 1\nSeed: {result['seed_run2']}", use_container_width=True)

            if result["shares_identical"]:
                st.error("🚨 Shares are IDENTICAL. An attacker replaying Session 1's seed can reconstruct Session 2's secret.")
            else:
                st.warning("Shares differ unexpectedly — check that the seed was actually reused.")

            st.image(result["diff_image"], caption="Difference image (black = identical pixels)", use_container_width=True)

    with col2:
        st.subheader("✅ QRNG — Replay Fails")
        st.markdown("No seed exists. Each session produces entirely different shares.")

        if st.button("Run QRNG Replay Test", type="primary"):
            with st.spinner("Generating shares twice with QRNG..."):
                result = replay_attack(image, generate_xor_shares, use_qrng=True)

            c1, c2 = st.columns(2)
            with c1:
                st.image(result["share1_run1"], caption="Session 1 Share 1", use_container_width=True)
            with c2:
                st.image(result["share1_run2"], caption="Session 2 Share 1", use_container_width=True)

            if not result["shares_identical"]:
                st.success("🔒 Shares are DIFFERENT. Replaying Session 1's material reveals nothing about Session 2.")
            else:
                st.error("Shares were identical — unexpected for QRNG.")

            st.image(result["diff_image"], caption="Difference image (bright = different pixels)", use_container_width=True)
