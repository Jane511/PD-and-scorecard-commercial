import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from .calibration import calibration_table
from .config import BASE_GOOD_BAD_ODDS, BASE_SCORE, PDO, PROPERTY_CANDIDATE_FEATURES, TEST_SIZE
from .monitoring import psi_table
from .policy import assign_score_band
from .transform import transform_to_woe
from .validation import auc_gini, decile_table, ks_table, score_band_default_rates
from .woe import fit_woe


def _score_from_pd(predicted_pd):
    factor = PDO / np.log(2)
    offset = BASE_SCORE - factor * np.log(BASE_GOOD_BAD_ODDS)
    predicted_pd = np.clip(predicted_pd, 1e-6, 1 - 1e-6)
    return offset + factor * np.log((1 - predicted_pd) / predicted_pd)


def fit_property_pd_scorecard(dataset: pd.DataFrame, seed: int) -> dict:
    model_df = dataset.copy()
    train_df, test_df = train_test_split(
        model_df,
        test_size=TEST_SIZE,
        random_state=seed,
        stratify=model_df["default_12m"],
    )

    iv_records = []
    woe_tables = {}
    binning_store = {}
    for feature in PROPERTY_CANDIDATE_FEATURES:
        table, spec, mapping = fit_woe(train_df[feature], train_df["default_12m"], feature)
        iv_records.append({"feature": feature, "iv": float(table["iv"].iloc[0])})
        woe_tables[feature] = table
        binning_store[feature] = {"spec": spec, "mapping": mapping}

    iv_summary = pd.DataFrame(iv_records).sort_values("iv", ascending=False).reset_index(drop=True)
    selected_features = iv_summary[iv_summary["iv"] >= 0.02]["feature"].tolist()
    if len(selected_features) < 8:
        selected_features = iv_summary.head(min(12, len(iv_summary)))["feature"].tolist()
    selected_features = selected_features[:20]

    selected_store = {feature: binning_store[feature] for feature in selected_features}
    selected_woe_table = pd.concat([woe_tables[feature] for feature in selected_features], ignore_index=True)

    train_woe = transform_to_woe(train_df, selected_store)
    test_woe = transform_to_woe(test_df, selected_store)

    model = LogisticRegression(max_iter=500, solver="lbfgs")
    model.fit(train_woe[selected_features], train_df["default_12m"])

    train_pred = model.predict_proba(train_woe[selected_features])[:, 1]
    test_pred = model.predict_proba(test_woe[selected_features])[:, 1]
    train_score = _score_from_pd(train_pred)
    test_score = _score_from_pd(test_pred)

    train_scored = train_df.copy()
    train_scored["predicted_pd"] = train_pred
    train_scored["score"] = train_score
    train_scored["score_band"] = assign_score_band(train_scored["predicted_pd"])
    train_scored["data_split"] = "train"

    test_scored = test_df.copy()
    test_scored["predicted_pd"] = test_pred
    test_scored["score"] = test_score
    test_scored["score_band"] = assign_score_band(test_scored["predicted_pd"])
    test_scored["data_split"] = "test"

    portfolio_scored = pd.concat([train_scored, test_scored], ignore_index=True)

    coefficients = pd.DataFrame(
        {
            "feature": selected_features,
            "coefficient": model.coef_[0],
        }
    )
    coefficients["odds_ratio"] = np.exp(coefficients["coefficient"])
    coefficients["direction"] = np.where(
        coefficients["coefficient"] < 0,
        "Higher WOE lowers default risk",
        "Higher WOE raises default risk",
    )
    coefficients = coefficients.sort_values("coefficient")

    factor = PDO / np.log(2)
    offset = BASE_SCORE - factor * np.log(BASE_GOOD_BAD_ODDS)
    intercept_share = model.intercept_[0] / max(len(selected_features), 1)
    offset_share = offset / max(len(selected_features), 1)
    coefficient_map = coefficients.set_index("feature")["coefficient"].to_dict()
    points_table = selected_woe_table.copy()
    points_table["beta"] = points_table["feature"].map(coefficient_map)
    points_table["points"] = offset_share - factor * (intercept_share + points_table["beta"] * points_table["woe"])

    train_metrics = auc_gini(train_scored["default_12m"], train_scored["predicted_pd"])
    test_metrics = auc_gini(test_scored["default_12m"], test_scored["predicted_pd"])
    metadata = pd.DataFrame(
        [
            {
                "train_auc": train_metrics["auc"],
                "test_auc": test_metrics["auc"],
                "train_gini": train_metrics["gini"],
                "test_gini": test_metrics["gini"],
                "base_score": BASE_SCORE,
                "base_good_bad_odds": BASE_GOOD_BAD_ODDS,
                "pdo": PDO,
                "n_features": len(selected_features),
                "portfolio_default_rate": portfolio_scored["default_12m"].mean(),
                "selected_features": "|".join(selected_features),
            }
        ]
    )

    band_order = ["A", "B", "C", "D", "E"]
    train_counts = train_scored["score_band"].value_counts().reindex(band_order, fill_value=0).values
    test_counts = test_scored["score_band"].value_counts().reindex(band_order, fill_value=0).values
    monitoring = psi_table(train_counts, test_counts, labels=band_order)

    return {
        "iv_summary": iv_summary,
        "woe_table": selected_woe_table,
        "coefficients": coefficients,
        "points_table": points_table,
        "train_scored": train_scored,
        "test_scored": test_scored,
        "portfolio_scored": portfolio_scored,
        "metadata": metadata,
        "calibration_table": calibration_table(test_scored, "predicted_pd"),
        "score_band_summary": score_band_default_rates(portfolio_scored, "score_band"),
        "decile_table": decile_table(test_scored, "score"),
        "ks_table": ks_table(test_scored, "score"),
        "monitoring_psi": monitoring,
        "selected_features": selected_features,
    }
