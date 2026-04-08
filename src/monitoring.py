import numpy as np
import pandas as pd


def psi_table(expected_counts, actual_counts, labels=None, eps: float = 1e-6) -> pd.DataFrame:
    expected_counts = np.asarray(expected_counts, dtype=float)
    actual_counts = np.asarray(actual_counts, dtype=float)

    expected_dist = expected_counts / max(expected_counts.sum(), eps)
    actual_dist = actual_counts / max(actual_counts.sum(), eps)
    expected_dist = np.where(expected_dist <= 0, eps, expected_dist)
    actual_dist = np.where(actual_dist <= 0, eps, actual_dist)

    psi_component = (actual_dist - expected_dist) * np.log(actual_dist / expected_dist)
    output = pd.DataFrame(
        {
            "band": labels if labels is not None else np.arange(len(expected_counts)),
            "expected_count": expected_counts,
            "actual_count": actual_counts,
            "expected_dist": expected_dist,
            "actual_dist": actual_dist,
            "psi_component": psi_component,
        }
    )
    output["psi_total"] = output["psi_component"].sum()
    return output
