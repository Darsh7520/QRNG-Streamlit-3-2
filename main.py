import sys
import os

# Ensure this script's own directory is on sys.path *before* anything else
# imports from it. Every page module already does this for its own sibling
# imports (see e.g. app_pages/xor_page.py) -- main.py needs the same guarantee
# so `from app_pages.xxx import render` resolves regardless of how Streamlit
# was launched or what the current working directory is.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Quantum Enhanced Visual Cryptography",
    page_icon="🔐",
    layout="wide"
)

# --- Sidebar ---
st.sidebar.title("🔐 QEVC Demo")
st.sidebar.markdown("Quantum Enhanced Visual Cryptography")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    [
        "🏠 Home",
        "🔑 XOR Share Generation",
        "🧩 Naor-Shamir Share Generation",
        "🌀 Bell-Pair Entangled VC",
        "🔗 Entanglement Correlation Analysis",
        "💣 Brute Force Attack",
        "🔁 Replay Attack",
        "📊 Statistical Analysis",
    ]
)

st.sidebar.divider()
st.sidebar.caption("Built with Qiskit · Streamlit · NumPy · Pillow")

# --- Pages ---

if page == "🏠 Home":
    st.title("Quantum Enhanced Visual Cryptography")
    st.markdown("""
    This application demonstrates three visual cryptography implementations and
    provides live security analysis comparing classical PRNG-based schemes against
    quantum-enhanced alternatives.

    ---

    ### Implementations
    | Scheme | Randomness | Correlation Source | Pixel Expansion | Reconstruction |
    |---|---|---|---|---|
    | XOR-based VC | QRNG / PRNG | Shared bitstream | None | Lossless |
    | Naor-Shamir (2,2) | QRNG / PRNG | Shared bitstream | 4x per dimension | Perceptual |
    | Bell-Pair Entangled VC | Quantum entanglement | Physical (measured), no shared secret | None | Perceptual (statistical) |

    ---

    ### Security Demonstrations
    - **Brute Force Attack** -- Show that PRNG shares can be cracked by seed recovery.
      QRNG shares cannot.
    - **Replay Attack** -- Show that PRNG produces identical shares every run.
      QRNG produces different shares every time.
    - **Entanglement Correlation Analysis** -- Show that Bell pairs achieve the
      correlation two shares need *without* a shared seed at all -- the same
      correlation a shared-seed PRNG gets, without that seed being a single
      point of failure.
    - **Statistical Analysis** -- Compare entropy and uniformity of PRNG vs QRNG shares.

    ---

    ### How to use
    1. Go to **XOR**, **Naor-Shamir**, or **Bell-Pair** Share Generation to generate shares.
    2. Use the **Attack** pages to demonstrate security properties.
    3. Use **Entanglement Correlation Analysis** and **Statistical Analysis** to compare randomness quality.
    """)

elif page == "🔑 XOR Share Generation":
    from app_pages.xor_page import render
    render()

elif page == "🧩 Naor-Shamir Share Generation":
    from app_pages.ns_page import render
    render()

elif page == "🌀 Bell-Pair Entangled VC":
    from app_pages.bell_page import render
    render()

elif page == "🔗 Entanglement Correlation Analysis":
    from app_pages.entanglement_page import render
    render()

elif page == "💣 Brute Force Attack":
    from app_pages.brute_force_page import render
    render()

elif page == "🔁 Replay Attack":
    from app_pages.replay_page import render
    render()

elif page == "📊 Statistical Analysis":
    from app_pages.stats_page import render
    render()
