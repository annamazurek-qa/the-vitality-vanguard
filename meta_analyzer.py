
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultra-simple meta analyzer for extractor JSONs.

How to use:
1) Put this file next to your JSONs (or anywhere).
2) Run:  python meta_analyzer_min.py
Outputs appear in ./meta_output next to this file.
"""

import os, json, glob
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------- SIMPLE DEFAULTS (edit if you want) ----------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INPATH = BASE_DIR                 # scans for *.json here
OUTDIR = os.path.join(BASE_DIR, "meta_output")
MIN_K = 2                         # min studies per (outcome,type) to pool
MAKE_PLOTS = True                 # set False to skip forest plots

Z = 1.96


def coerce_float(x):
    if x is None or (isinstance(x, str) and str(x).strip() == ""):
        return np.nan
    try:
        return float(x)
    except Exception:
        try:
            if str(x).lower() in {"nan", "none"}:
                return np.nan
        except Exception:
            pass
        return np.nan


def normalize_type(t: Optional[str]) -> Optional[str]:
    if t is None:
        return None
    t = str(t).strip().upper()
    aliases = {
        "MEAN DIFFERENCE": "MD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
        "HEDGE'S G": "SMD",
        "HEDGES G": "SMD",
        "COHEN D": "SMD",
        "COHEN'S D": "SMD",
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "LOG(RR)": "LOGRR",
        "LOG(OR)": "LOGOR",
        "LOG(HR)": "LOGHR",
    }
    return aliases.get(t, t)


def se_from_ci(ci_low, ci_high):
    lo, hi = coerce_float(ci_low), coerce_float(ci_high)
    if np.isnan(lo) or np.isnan(hi):
        return np.nan
    return (hi - lo) / (2 * Z)


class MetaAnalyzer:
    def __init__(self, json_paths: List[str], outdir: str, min_k: int = 2):
        self.json_paths = sorted(json_paths)
        self.outdir = outdir
        self.min_k = int(min_k)
        os.makedirs(self.outdir, exist_ok=True)
        self.forest_dir = os.path.join(self.outdir, "forest_plots")
        os.makedirs(self.forest_dir, exist_ok=True)

        self.effects_df: Optional[pd.DataFrame] = None
        self.pooled_df: Optional[pd.DataFrame] = None

    @staticmethod
    def resolve_json_paths(folder: str) -> List[str]:
        pattern = os.path.join(folder, "*.json")
        return sorted(glob.glob(pattern))

    @staticmethod
    def load_effect_rows(path: str) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        study = data.get("study_metadata", {}) or {}
        effects = data.get("effects_by_outcome", []) or []

        rows = []
        for e in effects:
            rows.append({
                "file": os.path.basename(path),
                "study_id": study.get("study_id") or study.get("doi") or study.get("title") or os.path.basename(path),
                "design": study.get("design"),
                "species": study.get("species"),
                "outcome": e.get("name"),
                "type": normalize_type(e.get("type")),
                "timepoint_weeks": coerce_float(e.get("timepoint_weeks")),
                "estimate": coerce_float(e.get("estimate")),
                "ci_low": coerce_float(e.get("ci_low")) if e.get("ci_low") is not None else np.nan,
                "ci_high": coerce_float(e.get("ci_high")) if e.get("ci_high") is not None else np.nan,
                "p_value": coerce_float(e.get("p_value")),
                "adjusted": e.get("adjusted"),
                "unit": e.get("unit"),
                "model_notes": e.get("model_notes"),
            })
        return rows

    @staticmethod
    def unit_consistent(group: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        units = [u for u in group["unit"].dropna().unique().tolist() if str(u).strip() != ""]
        if len(units) <= 1:
            return True, (units[0] if units else None)
        return False, None

    @staticmethod
    def dersimonian_laird(ests: np.ndarray, ses: np.ndarray) -> Tuple[float, Tuple[float, float], float, float]:
        w = 1.0 / (ses ** 2)
        fixed = np.sum(w * ests) / np.sum(w)
        q = np.sum(w * (ests - fixed) ** 2)
        k = len(ests)
        if k <= 1:
            tau2 = 0.0
            w_star = w
        else:
            c = np.sum(w) - (np.sum(w ** 2) / np.sum(w))
            tau2 = max(0.0, (q - (k - 1)) / c)
            w_star = 1.0 / (ses ** 2 + tau2)

        pooled = np.sum(w_star * ests) / np.sum(w_star)
        se_pooled = (1.0 / np.sum(w_star)) ** 0.5
        ci = (pooled - Z * se_pooled, pooled + Z * se_pooled)

        I2 = 0.0
        if k > 1 and q > 0:
            I2 = max(0.0, (q - (k - 1)) / q) * 100.0

        return pooled, ci, tau2, I2

    @staticmethod
    def readiness_reason(estimate, ci_low, ci_high):
        est = coerce_float(estimate)
        if np.isnan(est):
            return "No effect estimate"
        if np.isnan(se_from_ci(ci_low, ci_high)):
            return "Missing CI (or unparsable)"
        return "Ready"

    def build_effects(self) -> pd.DataFrame:
        all_rows = []
        for p in self.json_paths:
            try:
                rows = self.load_effect_rows(p)
                all_rows.extend(rows)
            except Exception as e:
                print(f"ERROR reading {p}: {e}")
        effects = pd.DataFrame(all_rows)
        if effects.empty:
            print("No effects found in JSONs.")
            self.effects_df = effects
            return effects

        effects["readiness"] = effects.apply(
            lambda r: self.readiness_reason(r["estimate"], r["ci_low"], r["ci_high"]), axis=1
        )
        effects["SE"] = effects.apply(lambda r: se_from_ci(r["ci_low"], r["ci_high"]), axis=1)
        self.effects_df = effects
        return effects

    def save_tables(self):
        if self.effects_df is None:
            return
        effects_csv = os.path.join(self.outdir, "effects.csv")
        readiness_csv = os.path.join(self.outdir, "readiness.csv")
        self.effects_df.to_csv(effects_csv, index=False)
        self.effects_df[["file", "study_id", "outcome", "type", "timepoint_weeks", "readiness"]].to_csv(
            readiness_csv, index=False
        )
        print(f"Saved: {effects_csv}")
        print(f"Saved: {readiness_csv}")

    def pool_groups(self, make_plots: bool = True) -> pd.DataFrame:
        if self.effects_df is None or self.effects_df.empty:
            self.pooled_df = pd.DataFrame()
            return self.pooled_df

        pooled_rows = []
        grouped = self.effects_df.groupby(["outcome", "type"], dropna=False)
        for (outcome, etype), g in grouped:
            g_ready = g[(g["readiness"] == "Ready")].copy()
            g_ready = g_ready.dropna(subset=["estimate", "SE"])

            ok_units, unit = self.unit_consistent(g_ready)
            if not ok_units:
                pooled_rows.append({
                    "outcome": outcome, "type": etype, "k": int(len(g_ready)),
                    "pooled": np.nan, "ci_low": np.nan, "ci_high": np.nan,
                    "tau2": np.nan, "I2": np.nan, "unit": None,
                    "note": "Unit mismatch within group; skipping pooling",
                })
                continue

            if len(g_ready) < MIN_K:
                pooled_rows.append({
                    "outcome": outcome, "type": etype, "k": int(len(g_ready)),
                    "pooled": np.nan, "ci_low": np.nan, "ci_high": np.nan,
                    "tau2": np.nan, "I2": np.nan, "unit": unit,
                    "note": f"Less than min-k ({MIN_K}); skipping pooling",
                })
                continue

            ests = g_ready["estimate"].values.astype(float)
            ses = g_ready["SE"].values.astype(float)

            pooled, (lo, hi), tau2, I2 = self.dersimonian_laird(ests, ses)
            pooled_row = {
                "outcome": outcome, "type": etype, "k": int(len(g_ready)),
                "pooled": pooled, "ci_low": lo, "ci_high": hi, "tau2": tau2, "I2": I2,
                "unit": unit, "note": "OK",
            }
            pooled_rows.append(pooled_row)

            if make_plots:
                outpng = os.path.join(self.forest_dir, f"{str(outcome).replace(' ','_')}__{etype or 'NA'}.png")
                try:
                    self.make_forest_plot(g_ready, pooled_row, outpng)
                except Exception as e:
                    print(f"Forest plot failed for {outcome}/{etype}: {e}")

        pooled_df = pd.DataFrame(pooled_rows)
        self.pooled_df = pooled_df

        pooled_csv = os.path.join(self.outdir, "pooled_summary.csv")
        pooled_df.to_csv(pooled_csv, index=False)
        print(f"Saved: {pooled_csv}")
        print(f"Forest plots: {self.forest_dir}")
        return pooled_df

    @staticmethod
    def make_forest_plot(group: pd.DataFrame, pooled_row: Dict[str, Any], outpath: str):
        g = group.copy().reset_index(drop=True)
        g["SE"] = g.apply(lambda r: se_from_ci(r["ci_low"], r["ci_high"]), axis=1)
        g = g.dropna(subset=["SE", "estimate"])

        labels = g["study_id"].tolist()
        ests = g["estimate"].values
        ses = g["SE"].values
        ci_l = ests - Z * ses
        ci_u = ests + Z * ses

        plt.figure(figsize=(7, 0.45 * max(4, len(g) + 3)))
        y = np.arange(len(g), 0, -1)
        for i, (lo, hi, e) in enumerate(zip(ci_l, ci_u, ests)):
            plt.hlines(y[i], lo, hi)
            plt.plot(e, y[i], "o")
        plt.axvline(pooled_row["pooled"], linestyle="--")
        plt.fill_betweenx([0, len(g) + 1], pooled_row["ci_low"], pooled_row["ci_high"], alpha=0.15)
        plt.yticks(y, labels, fontsize=8)
        plt.xlabel(f"Effect ({group['type'].iloc[0]})")
        plt.title(f"{group['outcome'].iloc[0]} — Random-effects (DL)")
        plt.tight_layout()
        plt.savefig(outpath, dpi=200)
        plt.close()

    def run(self, make_plots: bool = True):
        print(f"Scanning JSONs in: {INPATH}")
        print(f"Writing outputs to: {OUTDIR}")
        paths = self.resolve_json_paths(INPATH)
        if not paths:
            print("No JSONs found. Put your extractor JSONs into this folder.")
            return
        print(f"Found {len(paths)} JSON files.")
        self.json_paths = paths

        self.build_effects()
        self.save_tables()
        self.pool_groups(make_plots=make_plots)


if __name__ == "__main__":
    INPATH = "extractor_output/"
    OUTDIR = "meta_output/"
    MIN_K = 2                         # min studies per (outcome,type) to pool
    MAKE_PLOTS = True                 # set False to skip forest plots

    os.makedirs(OUTDIR, exist_ok=True)
    analyzer = MetaAnalyzer(json_paths=[], outdir=OUTDIR, min_k=MIN_K)
    analyzer.run(make_plots=MAKE_PLOTS)
