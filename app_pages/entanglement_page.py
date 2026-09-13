import streamlit as st
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bell_vc import correlation_test


def render():
    st.title("🔗 Entanglement Correlation Analysis")
    st.markdown("""
    Two-share visual cryptography needs the shares to be *correlated* — generated
    together so recombining them reveals the secret. The question this page
    answers: **how do you get two correlated random bit-streams without a shared
    secret an attacker could steal?**

    - **Independent PRNG streams** (no shared seed) — should show ~50% agreement:
      no usable correlation at all.
    - **Shared-seed PRNG streams** — ~100% agreement, but only because both sides
      know the same seed. A single leaked seed breaks the whole scheme (see the
      Brute Force and Replay Attack pages).
    - **Quantum entangled (Bell pair) streams** — ~100% agreement with **no
      shared secret at all**. The correlation is a physical property of the
      entangled state, not something computed from a key — there's no seed to
      leak, and the no-cloning theorem means an eavesdropper can't intercept one
      half without detectably disturbing it.
    """)

    st.divider()
    n_bits = st.slider("Number of bit-pairs to test", 100, 5000, 1000, step=100)

    if st.button("Run Correlation Test", type="primary"):
        with st.spinner("Generating independent PRNG streams..."):
            rng_a = np.random.default_rng(np.random.randint(0, 100000))
            rng_b = np.random.default_rng(np.random.randint(0, 100000))
            a_indep = rng_a.integers(0, 2, size=n_bits)
            b_indep = rng_b.integers(0, 2, size=n_bits)
            agreement_indep = float((a_indep == b_indep).mean())

        with st.spinner("Generating shared-seed PRNG streams..."):
            seed = int(np.random.randint(0, 100000))
            rng_shared_a = np.random.default_rng(seed)
            rng_shared_b = np.random.default_rng(seed)
            a_shared = rng_shared_a.integers(0, 2, size=n_bits)
            b_shared = rng_shared_b.integers(0, 2, size=n_bits)
            agreement_shared = float((a_shared == b_shared).mean())

        with st.spinner("Generating entangled Bell-pair streams (quantum)..."):
            agreement_quantum, _, _ = correlation_test(n_bits, shots_per_pixel=1)

        st.divider()
        st.subheader("Results")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Independent PRNG", f"{agreement_indep*100:.1f}%")
            st.caption("No shared secret → no usable correlation, as expected.")
        with c2:
            st.metric("Shared-seed PRNG", f"{agreement_shared*100:.1f}%")
            st.caption("Perfect correlation, but only because a secret seed is shared — a leaked seed leaks everything.")
        with c3:
            st.metric("Quantum Entangled", f"{agreement_quantum*100:.1f}%")
            st.caption("Perfect correlation with **no shared secret** — the correlation is physical, not computational.")

        st.divider()
        fig_data = {
            "Method": ["Independent PRNG", "Shared-seed PRNG", "Quantum Entangled"],
            "Agreement %": [agreement_indep * 100, agreement_shared * 100, agreement_quantum * 100],
            "Requires shared secret?": ["No (but useless)", "Yes (vulnerable)", "No"],
        }
        st.table(fig_data)

        if agreement_quantum > 0.9 and agreement_indep < 0.6:
            st.success(
                "Entangled Bell pairs reproduce the correlation of a shared secret "
                "without needing one — closing the exact vulnerability the Brute "
                "Force and Replay Attack pages demonstrate for seed-based PRNG shares."
            )
