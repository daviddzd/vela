"""Statistics for the experiment: 95 % confidence intervals and policy comparisons.

Design: common random numbers -> the 5 policies are PAIRED by replication (same crises, same visits).
Independent-groups tests (one-way ANOVA, Kruskal-Wallis) would ignore that pairing, so:
  - normality of the paired differences (policy - human_dispatcher) checked with Shapiro-Wilk
  - all normal  -> repeated-measures ANOVA (statsmodels AnovaRM) + paired t-tests vs human_dispatcher
  - otherwise   -> Friedman test (the paired version of Kruskal-Wallis) + Wilcoxon signed-rank vs human
  - pairwise p-values corrected with Holm (4 comparisons per metric and scenario)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.anova import AnovaRM
from statsmodels.stats.multitest import multipletests

POLICIES = ["nearest", "risk_priority", "risk_plus_live_traffic", "vela_timeout", "human_dispatcher"]
REFERENCE = "human_dispatcher"


def ci95(values: pd.Series) -> tuple[float, float, float, int]:
    v = values.dropna().to_numpy(dtype=float)
    n = len(v)
    if n == 0:
        return np.nan, np.nan, np.nan, 0
    mean = float(v.mean())
    if n < 2 or np.allclose(v, v[0]):
        return mean, mean, mean, n
    half = stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)
    return mean, mean - half, mean + half, n


def summary(runs: pd.DataFrame, metrics: list[str], group: list[str]) -> pd.DataFrame:
    rows = []
    for keys, g in runs.groupby(group):
        keys = keys if isinstance(keys, tuple) else (keys,)
        for m in metrics:
            mean, lo, hi, n = ci95(g[m])
            rows.append({**dict(zip(group, keys)), "metric": m, "mean": mean, "ci_low": lo, "ci_high": hi, "n": n})
    return pd.DataFrame(rows)


def compare(runs: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    out = []
    for scenario, g in runs.groupby("scenario"):
        for m in metrics:
            wide = g.pivot(index="replication", columns="policy", values=m)[POLICIES].dropna()
            if len(wide) < 5 or np.allclose(wide.to_numpy(), wide.to_numpy()[0, 0]):
                out.append({"scenario": scenario, "metric": m, "omnibus": "sin variación", "omnibus_p": np.nan,
                            "normal": None})
                continue
            diffs = {p: wide[p] - wide[REFERENCE] for p in POLICIES if p != REFERENCE}
            normal = all(np.allclose(d, d.iloc[0]) or stats.shapiro(d).pvalue > 0.05 for d in diffs.values())
            if normal:
                long = wide.reset_index().melt(id_vars="replication", var_name="policy", value_name="y")
                try:
                    res = AnovaRM(long, "y", "replication", within=["policy"]).fit()
                    omnibus, p_omni = "ANOVA de medidas repetidas", float(res.anova_table["Pr > F"].iloc[0])
                except Exception:  # noqa: BLE001 - singular designs fall back to Friedman
                    normal = False
            if not normal:
                omnibus, p_omni = "Friedman", float(stats.friedmanchisquare(*[wide[p] for p in POLICIES]).pvalue)
            raw = []
            for p, d in diffs.items():
                if np.allclose(d, 0):
                    raw.append(1.0)
                elif normal:
                    raw.append(float(stats.ttest_rel(wide[p], wide[REFERENCE]).pvalue))
                else:
                    raw.append(float(stats.wilcoxon(wide[p], wide[REFERENCE], zero_method="zsplit").pvalue))
            holm = multipletests(raw, method="holm")[1]
            row = {"scenario": scenario, "metric": m, "omnibus": omnibus, "omnibus_p": p_omni, "normal": normal,
                   "pairwise_test": "t pareada" if normal else "Wilcoxon de rangos con signo"}
            for (p, d), pr, ph in zip(diffs.items(), raw, holm):
                row[f"{p}_diff_mean"] = float(d.mean())
                row[f"{p}_p_raw"] = pr
                row[f"{p}_p_holm"] = float(ph)
            out.append(row)
    return pd.DataFrame(out)
