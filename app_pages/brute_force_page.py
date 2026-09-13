import streamlit as st
from PIL import Image
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xor_vc import generate_xor_shares
from attacks import brute_force_attack


def render():
    st.title(" Brute Force Seed Recovery Attack")
    st.markdown("""
    This demonstration shows how an attacker who intercepts **Share 2** can attempt to
    recover the secret image by brute-forcing the PRNG seed.

    - **PRNG mode**: The attacker succeeds because the seed space is finite and predictable.
    - **QRNG mode**: The attack is impossible because no seed exists to recover.
    """)

    st.divider()

    uploaded = st.file_uploader("Upload a secret image for this demonstration", type=["png", "jpg", "jpeg", "bmp"])

    if not uploaded:
        st.info("Upload an image to begin the demonstration.")
        return

    image = Image.open(uploaded).convert('L')
    st.image(image, caption=f"Secret Image ({image.width}×{image.height})", width=200)
    if image.width * image.height > 128 * 128:
        st.caption(
            "⚠️ Large images mean a large per-attempt cost even with the optimized search "
            "loop — expect the PRNG attack to take noticeably longer at big search ranges."
        )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⚠️ PRNG Attack — Attacker Succeeds")
        seed_range = st.slider(
            "Seed search range (attacker tries seeds 0 to N)",
            10, 100000, 1000,
            help="The true seed is drawn from [0, 100000). Search range must reach it to succeed."
        )

        if st.button("Run PRNG Attack", type="primary"):
            with st.spinner("Generating PRNG shares..."):
                share1, share2, true_seed = generate_xor_shares(image, use_qrng=False)

            st.image(share2, caption="Intercepted Share 2 (attacker has this)", width=200)
            st.caption(f"True seed used during generation: `{true_seed}` (hidden from attacker)")

            progress_bar = st.progress(0)
            status = st.empty()
            preview = st.empty()

            def update(attempt, total, candidate):
                progress_bar.progress(min((attempt + 1) / total, 1.0))
                status.markdown(f"Trying seed `{attempt}` of `{total}`...")
                if candidate is not None:
                    preview.image(candidate, caption=f"Attacker's attempt at seed {attempt}", width=200)

            result = brute_force_attack(share2, image, true_seed, seed_range, update)
            progress_bar.progress(1.0)

            if result["success"]:
                st.error(f"🚨 Attack succeeded in {result['attempts']} attempts ({result['time_taken']}s)")
                st.image(result["recovered"], caption="Image recovered by attacker", width=200)
            else:
                st.warning(f"Seed not found in range 0–{seed_range} (true seed: {true_seed}). Try increasing the range.")

    with col2:
        st.subheader("✅ QRNG Attack — Attacker Fails")
        st.markdown("""
        With QRNG there is no seed. The attacker can try every possible value forever
        and will never reconstruct the secret image because the random matrix $R$ was
        generated from quantum physical events that cannot be reproduced.
        """)

        if st.button("Attempt QRNG Attack"):
            with st.spinner("Generating QRNG shares..."):
                share1_q, share2_q, _ = generate_xor_shares(image, use_qrng=True)

            st.image(share2_q, caption="Intercepted QRNG Share 2", width=200)
            s2_arr = np.array(share2_q.convert('L'), dtype=np.uint8)

            st.info("Attacker tries random seeds...")
            attempt_imgs = []
            for seed in range(5):
                rng = np.random.default_rng(seed)
                fake_s1 = rng.integers(0, 256, size=s2_arr.shape, dtype=np.uint8)
                fake_recovery = np.bitwise_xor(fake_s1, s2_arr)
                attempt_imgs.append(Image.fromarray(fake_recovery))

            cols = st.columns(5)
            for i, img in enumerate(attempt_imgs):
                with cols[i]:
                    st.image(img, caption=f"Seed {i}", use_container_width=True)

            st.success("🔒 Every attempt produces random noise. Attack failed.")
