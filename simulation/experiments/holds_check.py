"""Does the reservation of the proposed candidate hurt the other requests?
Paired comparison WITH vs WITHOUT holds: normal scenario, the operating policy (vela_timeout), 30 replications.
Run:  docker compose run --rm sim python -m simulation.experiments.holds_check
Output: simulation/results/holds_check.csv
"""
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from simulation.experiments.run import RESULTS
from simulation.sirag.model import Params
from simulation.sirag.runner import run_one

METRICS = ["unattended_pct", "medium_wait_p90_min", "low_wait_p90_min"]


def main() -> None:
    jobs = [Params("vela_timeout", "normal", r, holds=h) for r in range(30) for h in (True, False)]
    with Pool() as pool:
        rows = pool.map(run_one, jobs)
    df = pd.DataFrame(rows)
    df["holds"] = [p.holds for p in jobs]
    out = []
    for m in METRICS:
        w = df.pivot(index="replication", columns="holds", values=m).dropna()
        d = w[True] - w[False]
        if np.allclose(d, 0):
            p = 1.0
            test = "sin diferencias"
        elif stats.shapiro(d).pvalue > 0.05:
            p, test = float(stats.ttest_rel(w[True], w[False]).pvalue), "t pareada"
        else:
            p, test = float(stats.wilcoxon(w[True], w[False], zero_method="zsplit").pvalue), "Wilcoxon"
        out.append({"metric": m, "with_holds": w[True].mean(), "without_holds": w[False].mean(),
                    "diff_mean": d.mean(), "test": test, "p_raw": p})
    res = pd.DataFrame(out)
    res["p_holm"] = multipletests(res["p_raw"], method="holm")[1]
    res.to_csv(RESULTS / "holds_check.csv", index=False)
    print(res.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
