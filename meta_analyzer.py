
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

Z = 1.96

# --- Add this helper near the top (imports: os, json, math, glob already available) ---
def _impute_ci_from_raw(json_paths, outdir):
    """
    Fill missing CIs for continuous MDs using follow-up or change stats
    when both arms are present at the same outcome/timepoint.

    Writes updated copies to {outdir}/ci_imputed/.
    """
    import os, json, math

    outdir_ci = os.path.join(outdir, "ci_imputed")
    os.makedirs(outdir_ci, exist_ok=True)
    Z = 1.96

    def _as_list_of_dicts(x):
        if x is None:
            return []
        if isinstance(x, dict):
            return [x]
        if isinstance(x, list):
            return [i for i in x if isinstance(i, dict)]
        return []

    def _f(x):
        try:
            return float(x)
        except Exception:
            return None

    def _i(x):
        try:
            return int(x)
        except Exception:
            v = _f(x)
            return int(v) if v is not None else None

    def _classify_arm(arm_name, exposure_label, comparator_label):
        """Return 'intervention' | 'control' | None based on simple heuristics."""
        s = str(arm_name or "").lower()
        exp = str(exposure_label or "").lower()
        comp = str(comparator_label or "").lower()

        # obvious control markers
        control_tokens = ["placebo", "control", "standard care", "usual care", "no treatment", "non-use", "non use"]
        if any(tok in s for tok in control_tokens) or (comp and comp in s):
            return "control"

        # obvious intervention markers
        if exp and exp in s:
            return "intervention"
        intervention_tokens = ["resveratrol", "metformin"]
        if any(tok in s for tok in intervention_tokens) and not any(tok in s for tok in control_tokens):
            return "intervention"

        return None

    def _pair_stats(rows, exposure_label, comparator_label, mean_key, sd_key):
        """
        Try to find one intervention and one control row with given keys and n.
        Returns (md, ci_low, ci_high, unit) or None.
        """
        # index by arm name
        by_arm = {}
        for r in rows:
            arm = r.get("arm_name")
            if not isinstance(arm, str):
                continue
            by_arm.setdefault(arm, []).append(r)

        # flatten to one row per arm (prefer row that has the needed fields)
        arms = {}
        for arm, lst in by_arm.items():
            best = None
            for r in lst:
                m, s, n = _f(r.get(mean_key)), _f(r.get(sd_key)), _i(r.get("n"))
                if m is not None and s is not None and n is not None:
                    best = r
                    break
            if best is not None:
                arms[arm] = best

        if len(arms) < 2:
            return None

        # try to classify
        classified = {}
        for arm, r in arms.items():
            tag = _classify_arm(arm, exposure_label, comparator_label)
            if tag:
                classified[tag] = (arm, r)

        # if classification failed but we have exactly two arms, pick a reasonable default:
        if "intervention" not in classified or "control" not in classified:
            if len(arms) == 2:
                a_name, b_name = list(arms.keys())
                # prefer the one that doesn't look like control as intervention
                a_tag = _classify_arm(a_name, exposure_label, comparator_label)
                b_tag = _classify_arm(b_name, exposure_label, comparator_label)
                # choose intervention as the one not explicitly control
                if a_tag == "control":
                    classified["control"] = (a_name, arms[a_name])
                    classified["intervention"] = (b_name, arms[b_name])
                elif b_tag == "control":
                    classified["control"] = (b_name, arms[b_name])
                    classified["intervention"] = (a_name, arms[a_name])
                else:
                    # last resort: alphabetical, but skip to avoid wrong sign
                    return None
            else:
                return None

        _, a = classified.get("intervention")
        _, b = classified.get("control")
        if a is None or b is None:
            return None

        m1, s1, n1 = _f(a.get(mean_key)), _f(a.get(sd_key)), _i(a.get("n"))
        m0, s0, n0 = _f(b.get(mean_key)), _f(b.get(sd_key)), _i(b.get("n"))
        if None in (m1, s1, n1, m0, s0, n0):
            return None

        md = m1 - m0
        se = ((s1**2) / n1 + (s0**2) / n0) ** 0.5
        unit = a.get("units") or b.get("units")
        return md, md - Z * se, md + Z * se, unit

    updated = []
    for p in json_paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        raw = _as_list_of_dicts(data.get("outcomes_raw"))
        if not raw:
            continue

        exp = (data.get("exposure") or {}).get("label")
        comp = (data.get("exposure") or {}).get("comparator")

        # group raw rows by (name, timepoint_weeks)
        groups = {}
        for r in raw:
            # guard in case a stray non-dict slipped through
            if not isinstance(r, dict):
                continue
            key = (r.get("name"), r.get("timepoint_weeks"))
            groups.setdefault(key, []).append(r)

        changed = False
        for (name, tp), rows in groups.items():
            # try follow-up first, then change scores
            res = _pair_stats(rows, exp, comp, "followup_mean", "followup_sd")
            if res is None:
                res = _pair_stats(rows, exp, comp, "change_mean", "change_sd")
            if res is None:
                continue

            est, lo, hi, unit = res
            efs = data.get("effects_by_outcome") or []
            attached = False

            for e in efs:
                if e.get("name") == name and (e.get("timepoint_weeks") == tp or (e.get("timepoint_weeks") is None and tp is None)):
                    # only fill CIs if missing
                    if e.get("ci_low") is None and e.get("ci_high") is None:
                        e["ci_low"] = round(lo, 4)
                        e["ci_high"] = round(hi, 4)
                        if e.get("estimate") is None:
                            e["estimate"] = round(est, 4)
                        e["unit"] = e.get("unit") or unit
                        e["notes"] = (e.get("notes") or "") + " [CI imputed from raw (unadjusted)]"
                        changed = True
                        attached = True
                        break

            if not attached:
                # append a new, explicitly unadjusted MD effect
                efs.append({
                    "name": name, "type": "MD", "timepoint_weeks": tp,
                    "estimate": round(est, 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4),
                    "adjusted": False, "unit": unit, "subgroup": None,
                    "notes": "Effect computed from raw (unadjusted)"
                })
                data["effects_by_outcome"] = efs
                changed = True

        if changed:
            outp = os.path.join(outdir_ci, os.path.basename(p))
            with open(outp, "w", encoding="utf-8") as w:
                json.dump(data, w, ensure_ascii=False, indent=2)
            updated.append(outp)

    return updated

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
    MIN_K = 2
    MAKE_PLOTS = True

    os.makedirs(OUTDIR, exist_ok=True)

    # NEW: impute missing CIs into copies under OUTDIR/ci_imputed/
    json_paths = sorted(glob.glob(os.path.join(INPATH, "*.json")))
    _impute_ci_from_raw(json_paths, OUTDIR)

    # Proceed with your usual analyzer on the originals or on the ci_imputed copies
    analyzer = MetaAnalyzer(json_paths=[], outdir=OUTDIR, min_k=MIN_K)
    analyzer.run(make_plots=MAKE_PLOTS)
