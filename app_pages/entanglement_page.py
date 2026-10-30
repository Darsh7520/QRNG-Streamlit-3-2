import math
import os
import sys

import numpy as np
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from entanglement import run_circuit_batch


def render():
    st.title("Entanglement Correlation Analysis")
    st.markdown("""
    Compare classical bit streams with the same quantum circuit logic used by
    the Bell-Pair share-generation page. Quantum measurements run locally in
    Qiskit's Aer simulator.

    - **Independent PRNG streams:** about 50% agreement.
    - **Shared-seed PRNG streams:** 100% agreement when both streams use the same seed.
    - **Black-pixel circuit (theta = 0):** Bell-pair outcomes agree 100% of the time,
      with P(A OR B = 1) about 0.50.
    - **White-pixel circuit (theta = pi/2):** rotating the second qubit reduces
      agreement to about 50%, with P(A OR B = 1) about 0.75.

    This difference in joint measurement statistics carries the image information
    in `entanglement.py`. Each tested pair uses one measurement shot so agreement
    measures raw outcomes rather than majority-vote share bits.
    """)

    st.divider()
    n_bits = st.slider("Number of bit-pairs to test", 100, 5000, 1000, step=100)

    if st.button("Run Correlation Test", type="primary"):
        with st.spinner("Generating classical bit streams..."):
            a_indep = np.random.default_rng().integers(0, 2, size=n_bits)
            b_indep = np.random.default_rng().integers(0, 2, size=n_bits)
            seed = int(np.random.default_rng().integers(0, 100000))
            a_shared = np.random.default_rng(seed).integers(0, 2, size=n_bits)
            b_shared = np.random.default_rng(seed).integers(0, 2, size=n_bits)

        with st.spinner("Running the black- and white-pixel entanglement circuits..."):
            a_black, b_black, p_black = run_circuit_batch(
                theta=0.0, n_pixels=n_bits, shots_per_pixel=1,
            )
            a_white, b_white, p_white = run_circuit_batch(
                theta=math.pi / 2.0, n_pixels=n_bits, shots_per_pixel=1,
            )

        st.session_state["entanglement_correlation_result"] = {
            "n_bits": n_bits,
            "agreement": [
                float((a_indep == b_indep).mean()),
                float((a_shared == b_shared).mean()),
                float((a_black == b_black).mean()),
                float((a_white == b_white).mean()),
            ],
            "p_or": [
                float(np.logical_or(a_indep, b_indep).mean()),
                float(np.logical_or(a_shared, b_shared).mean()),
                float(p_black.mean()),
                float(p_white.mean()),
            ],
        }

    result = st.session_state.get("entanglement_correlation_result")
    if result is None:
        return

    st.divider()
    st.subheader("Results")
    st.caption(f"Results from {result['n_bits']} bit-pairs per method, one shot per pair.")
    methods = ["Independent PRNG", "Shared-seed PRNG", "Black-pixel circuit", "White-pixel circuit"]
    for column, method, agreement in zip(st.columns(4), methods, result["agreement"]):
        with column:
            st.metric(method, f"{agreement * 100:.1f}% agreement")

    st.table({
        "Method": methods,
        "Agreement %": [value * 100 for value in result["agreement"]],
        "Expected agreement %": [50.0, 100.0, 100.0, 50.0],
        "P(A OR B = 1)": result["p_or"],
        "Expected P(A OR B = 1)": [0.75, 0.50, 0.50, 0.75],
    })
    st.info(
        "The black- and white-pixel circuits use the same run_circuit_batch function "
        "as image share generation. Finite samples cause variation around the expected "
        "probabilities. This simulator comparison demonstrates correlation; it does "
        "not establish cryptographic security or test for eavesdropping."
    )
