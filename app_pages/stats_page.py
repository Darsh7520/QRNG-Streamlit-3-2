import streamlit as st
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xor_vc import generate_xor_shares
from attacks import analyze_share


def render():
    st.title("📊 Statistical Analysis")
    st.markdown("""
    A truly random share should have:
    - **Maximum entropy** close to 8.0 bits per pixel
    - **Uniform pixel distribution** across all 256 values
    - **High chi-square p-value** indicating no detectable pattern

    This page compares PRNG and QRNG shares on these metrics side by side.
    """)

    st.divider()

    uploaded = st.file_uploader("Upload a secret image", type=["png", "jpg", "jpeg", "bmp"])

    if not uploaded:
        st.info("Upload an image to begin analysis.")
        return

    image = Image.open(uploaded).convert('L').resize((128, 128))
    st.image(image, caption="Secret Image (resized to 128×128)", width=200)

    if st.button("Run Statistical Comparison", type="primary"):

        with st.spinner("Generating PRNG share..."):
            prng_s1, _, prng_seed = generate_xor_shares(image, use_qrng=False)

        with st.spinner("Generating QRNG share..."):
            qrng_s1, _, _ = generate_xor_shares(image, use_qrng=True)

        prng_stats = analyze_share(prng_s1)
        qrng_stats = analyze_share(qrng_s1)

        st.divider()
        st.subheader("Results")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### PRNG Share")
            st.image(prng_s1, caption=f"PRNG Share (seed: {prng_seed})", use_container_width=True)
            st.metric("Shannon Entropy", f"{prng_stats['entropy']} / 8.0 bits")
            st.metric("Chi-Square Statistic", f"{prng_stats['chi_square_stat']}")
            st.metric("Chi-Square p-value", f"{prng_stats['chi_square_p']}")

            if prng_stats['chi_square_p'] < 0.05:
                st.error("Pattern detected: distribution is not uniform.")
            else:
                st.success("Distribution appears uniform.")

        with col2:
            st.markdown("### QRNG Share")
            st.image(qrng_s1, caption="QRNG Share", use_container_width=True)
            st.metric("Shannon Entropy", f"{qrng_stats['entropy']} / 8.0 bits")
            st.metric("Chi-Square Statistic", f"{qrng_stats['chi_square_stat']}")
            st.metric("Chi-Square p-value", f"{qrng_stats['chi_square_p']}")

            if qrng_stats['chi_square_p'] < 0.05:
                st.error("Pattern detected: distribution is not uniform.")
            else:
                st.success("Distribution appears uniform.")

        st.divider()
        st.subheader("Pixel Value Distribution")

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        axes[0].bar(range(256), prng_stats['histogram'], color='#e05c5c', alpha=0.8, width=1)
        axes[0].axhline(y=image.width * image.height / 256, color='black',
                        linestyle='--', linewidth=1, label='Ideal uniform')
        axes[0].set_title(f"PRNG Share Distribution\nEntropy: {prng_stats['entropy']} bits")
        axes[0].set_xlabel("Pixel Value")
        axes[0].set_ylabel("Frequency")
        axes[0].legend()

        axes[1].bar(range(256), qrng_stats['histogram'], color='#5c9ee0', alpha=0.8, width=1)
        axes[1].axhline(y=image.width * image.height / 256, color='black',
                        linestyle='--', linewidth=1, label='Ideal uniform')
        axes[1].set_title(f"QRNG Share Distribution\nEntropy: {qrng_stats['entropy']} bits")
        axes[1].set_xlabel("Pixel Value")
        axes[1].set_ylabel("Frequency")
        axes[1].legend()

        plt.tight_layout()
        st.pyplot(fig)

        st.divider()
        st.subheader("Summary")
        st.table({
            "Metric": ["Shannon Entropy", "Chi-Square Statistic", "Chi-Square p-value", "Max Possible Entropy"],
            "PRNG Share": [
                prng_stats['entropy'],
                prng_stats['chi_square_stat'],
                prng_stats['chi_square_p'],
                "8.0 bits"
            ],
            "QRNG Share": [
                qrng_stats['entropy'],
                qrng_stats['chi_square_stat'],
                qrng_stats['chi_square_p'],
                "8.0 bits"
            ]
        })
