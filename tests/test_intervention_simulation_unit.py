"""Unit tests for Intervention Simulation."""

import numpy as np

from hygeia_graph.intervention_simulation import (
    build_intervention_table,
    build_signed_adjacency,
    simulate_intervention,
)


def test_build_signed_adjacency_symmetry():
    """Test adjacency matrix construction."""
    res = {
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "edges": [
            {"source": "A", "target": "B", "weight": 0.5},
            {"source": "B", "target": "C", "weight": -0.2},
        ],
    }

    ids, A = build_signed_adjacency(res, threshold=0.0)

    assert len(ids) == 3
    assert ids == ["A", "B", "C"]

    # Check symmetry
    # A-B = 0.5
    idx_A, idx_B = 0, 1
    assert A[idx_A, idx_B] == 0.5
    assert A[idx_B, idx_A] == 0.5

    # B-C = -0.2
    idx_C = 2
    assert A[idx_B, idx_C] == -0.2
    assert A[idx_C, idx_B] == -0.2

    # Diagonal 0
    assert A[0, 0] == 0


def test_simulation_one_step():
    """Test 1-step propagation."""
    # Chain A --(1.0)--> B --(0.5)--> C
    # intervene A delta=1
    # Expect B=1.0, C=0 (since 1 step)

    ids = ["A", "B", "C"]
    A = np.zeros((3, 3))
    A[0, 1] = A[1, 0] = 1.0
    A[1, 2] = A[2, 1] = 0.5

    # Normalized? max=1.0, so no change
    res = simulate_intervention(
        ids, A, intervene_node="A", delta=1.0, steps=1, damping=1.0, normalize_weights=True
    )

    eff = res["effects"]
    assert eff["B"] == 1.0
    assert eff["C"] == 0.0  # Not reached in 1 step


def test_simulation_two_steps_damped():
    """Test 2-step propagation with damping."""
    # Chain A --(1.0)--> B --(1.0)--> C
    # Normalize: max=1.0
    # Steps=2, Damping=0.5
    # Step 1: A->B effect = delta * A_ab = 1 * 1 = 1
    # Step 2: B->C effect = delta * damping^1 * (A^2)_ac
    # A^2 (path length 2) A->B->C = 1*1 = 1
    # Effect = 1 * 0.5 * 1 = 0.5

    ids = ["A", "B", "C"]
    A = np.zeros((3, 3))
    A[0, 1] = A[1, 0] = 1.0
    A[1, 2] = A[2, 1] = 1.0

    res = simulate_intervention(
        ids, A, intervene_node="A", delta=1.0, steps=2, damping=0.5, normalize_weights=True
    )

    eff = res["effects"]
    assert eff["B"] == 1.0  # Step 1 + Step 2(0)
    assert eff["C"] == 0.5  # Step 2

    # Does A get reflected effect?
    # Step 2: B->A. A^2_aa via B = 1.
    # Effect = 1 * 0.5 * 1 = 0.5. But simulate_intervention explicitly zeroes self-effect.
    assert "A" not in eff


def test_table_construction():
    """Test dataframe building."""
    ids = ["A", "B"]
    eff = {"B": 0.5}

    df = build_intervention_table(None, ids, eff, input_node="A")

    assert len(df) == 1
    assert df.iloc[0]["node_id"] == "B"
    assert df.iloc[0]["effect"] == 0.5
    assert df.iloc[0]["direction"] == "increase"
