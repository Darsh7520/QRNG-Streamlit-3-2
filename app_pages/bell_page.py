import streamlit as st
from PIL import Image
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bell_vc import generate_bell_shares, combine_bell_shares_exact, combine_bell_shares_statistical


def render():
    st.title(" Bell-Pair Entangled Visual Cryptography")
    st.markdown("""
    Generates two shares directly from entangled Bell pairs instead of a QRNG/PRNG
    bitstream. Unlike Naor-Shamir, there is **no pixel expansion** — one secret
    pixel maps to exactly one pixel per share.

    The trade-off: each individual share bit's own outcome is exactly 50/50 no
    matter what the secret pixel is — only the *joint correlation* between the
    two shares carries information. So a single physical stack is noisy; a clean
    image needs the full measurement statistics from many quantum "shots" per pixel.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded = st.file_uploader("Upload a secret image", type=["png", "jpg", "jpeg", "bmp"])
        shots = st.slider(
            "Shots per pixel (quantum measurements)", 1, 500, 100,
            help="More shots → cleaner statistical reconstruction. Has no effect on the exact physical stack."
        )
        st.caption("Recommended: small images (32×32–64×64) — one quantum circuit runs per pixel batch.")

        if uploaded:
            image = Image.open(uploaded)
            st.image(image, caption=f"Secret Image ({image.width}×{image.height})", use_container_width=True)

    with col2:
        if uploaded and st.button("Generate Entangled Shares", type="primary"):
            image = Image.open(uploaded)
            with st.spinner("Running entangled quantum circuits..."):
                share1, share2, p_or_map, secret = generate_bell_shares(image, shots_per_pixel=shots)

            st.session_state["bell_share1"] = share1
            st.session_state["bell_share2"] = share2
            st.session_state["bell_p_or_map"] = p_or_map
            st.success(f"Shares generated from entangled Bell pairs ({shots} shots/pixel). No seed exists.")

    if "bell_share1" in st.session_state:
        st.divider()
        st.subheader("Generated Shares")
        c1, c2 = st.columns(2)
        with c1:
            st.image(st.session_state["bell_share1"], caption="Share 1", use_container_width=True)
        with c2:
            st.image(st.session_state["bell_share2"], caption="Share 2", use_container_width=True)

        st.divider()
        st.subheader("Reconstruction")
        r1, r2 = st.columns(2)
        with r1:
            st.markdown("**Physical stack (OR)**")
            if st.button("Stack Shares → Exact"):
                exact = combine_bell_shares_exact(
                    st.session_state["bell_share1"], st.session_state["bell_share2"]
                )
                st.image(exact, caption="Literal physical stack", use_container_width=True)
                st.info("What overlaying the two printed shares actually looks like — noisy, since a single stacked pixel carries little information on its own.")
        with r2:
            st.markdown("**Statistical reconstruction**")
            if st.button("Reconstruct from Shot Statistics"):
                recon = combine_bell_shares_statistical(st.session_state["bell_p_or_map"])
                st.image(recon, caption="Reconstructed from quantum measurement statistics", use_container_width=True)
                st.success("Uses the full per-pixel measurement statistics rather than one physical stack — much cleaner, but needs the digital shot data, not just the two printed shares.")
