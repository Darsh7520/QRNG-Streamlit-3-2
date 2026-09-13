from qiskit import QuantumCircuit
from qiskit_aer import Aer
import numpy as np


def qrng_batch(n_bits: int) -> np.ndarray:
    """
    Generate n_bits truly random bits using a 256-qubit Hadamard circuit.
    Each circuit execution yields 256 bits. Repeats until enough bits collected.
    Returns np.ndarray of shape (n_bits,), dtype=uint8.
    """
    bits = []
    backend = Aer.get_backend('qasm_simulator')
    while len(bits) < n_bits:
        qc = QuantumCircuit(256, 256)
        qc.h(range(256))
        qc.measure(range(256), range(256))
        job = backend.run(qc, shots=1, memory=True)
        bitstring = job.result().get_memory(qc)[0]
        bits.extend(int(b) for b in bitstring)
    return np.array(bits[:n_bits], dtype=np.uint8)
