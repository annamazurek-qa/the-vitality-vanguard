"""
PRISMA Flow Diagram and Forest Plot Visualization

This module generates publication-ready visualizations for systematic reviews:
1. PRISMA flow diagram showing the screening process
2. Forest plot for meta-analysis results (placeholder for Module 5 integration)
"""

import json
from typing import Dict, Optional, List
from pathlib import Path

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib")


def create_prisma_flow_diagram(
    prisma_data: Dict,
    output_path: str,
    title: Optional[str] = None,
    dpi: int = 300
) -> None:
    """
    Generate a PRISMA 2020 compliant flow diagram.

    Args:
        prisma_data: Dictionary with PRISMA statistics (from make_prisma.py output)
        output_path: Path to save the PNG/PDF file
        title: Optional title for the diagram
        dpi: Resolution for the output image (default: 300)

    PRISMA Structure:
        [Identification] → Total records identified from databases
        [Screening] → Records screened (TA) → Records excluded (with reasons)
        [Eligibility] → Full-texts assessed → Full-texts excluded (with reasons)
        [Included] → Studies included in review
    """
    if not HAS_MATPLOTLIB:
        raise RuntimeError("matplotlib is required for visualization. Install with: pip install matplotlib")

    # Extract counts (support both old and new formats)
    total_citations = prisma_data.get("total_citations", prisma_data.get("screened", 0))
    ta_screened = prisma_data.get("ta_screened", prisma_data.get("screened", 0))
    ta_excluded = prisma_data.get("ta_excluded", 0)
    ta_included = ta_screened - ta_excluded

    ft_assessed = prisma_data.get("ft_assessed", prisma_data.get("fulltext_assessed", 0))
    ft_excluded = prisma_data.get("ft_excluded", prisma_data.get("fulltext_excluded", 0))
    ft_included = prisma_data.get("ft_included", prisma_data.get("included", 0))

    # Parse reasons (might be combined or separate)
    all_reasons = prisma_data.get("reasons", {})
    ta_reasons = prisma_data.get("ta_exclusion_reasons", {})
    ft_reasons = prisma_data.get("ft_exclusion_reasons", {})

    # If reasons are combined, separate them by common patterns
    if not ta_reasons and not ft_reasons and all_reasons:
        ta_reasons = {k: v for k, v in all_reasons.items()
                     if k in ["low_ml_score", "negative_kw", "maybe"]}
        ft_reasons = {k: v for k, v in all_reasons.items()
                     if k not in ta_reasons}

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 14))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')

    # Title
    if title:
        ax.text(5, 13.5, title, ha='center', va='top', fontsize=14, fontweight='bold')

    # Box styling
    box_style = dict(boxstyle='round,pad=0.5', facecolor='lightblue', edgecolor='black', linewidth=2)
    exclude_style = dict(boxstyle='round,pad=0.5', facecolor='lightcoral', edgecolor='black', linewidth=2)
    include_style = dict(boxstyle='round,pad=0.5', facecolor='lightgreen', edgecolor='black', linewidth=2)

    # IDENTIFICATION STAGE
    y_pos = 12
    ax.text(5, y_pos, f"Records identified from databases\n(n = {total_citations})",
            ha='center', va='center', bbox=box_style, fontsize=11, fontweight='bold')

    # Arrow down
    ax.annotate('', xy=(5, y_pos - 0.8), xytext=(5, y_pos - 0.3),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'))

    # SCREENING STAGE
    y_pos = 10.5
    ax.text(5, y_pos, f"Records screened (Title/Abstract)\n(n = {ta_screened})",
            ha='center', va='center', bbox=box_style, fontsize=11, fontweight='bold')

    # TA Exclusions (right side)
    ax.annotate('', xy=(7.5, y_pos), xytext=(6, y_pos),
                arrowprops=dict(arrowstyle='->', lw=2, color='red'))

    exclusion_text = f"Records excluded (n = {ta_excluded})"
    if ta_reasons:
        exclusion_text += "\n" + "\n".join([f"  • {reason}: {count}"
                                            for reason, count in sorted(ta_reasons.items())])

    ax.text(8.5, y_pos, exclusion_text,
            ha='left', va='center', bbox=exclude_style, fontsize=9)

    # Arrow down to eligibility
    ax.annotate('', xy=(5, y_pos - 1.5), xytext=(5, y_pos - 0.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'))

    # ELIGIBILITY STAGE
    y_pos = 8.5
    ax.text(5, y_pos, f"Full-text articles assessed for eligibility\n(n = {ft_assessed})",
            ha='center', va='center', bbox=box_style, fontsize=11, fontweight='bold')

    # FT Exclusions (right side)
    if ft_excluded > 0:
        ax.annotate('', xy=(7.5, y_pos), xytext=(6, y_pos),
                    arrowprops=dict(arrowstyle='->', lw=2, color='red'))

        ft_exclusion_text = f"Full-text excluded (n = {ft_excluded})"
        if ft_reasons:
            ft_exclusion_text += "\n" + "\n".join([f"  • {reason}: {count}"
                                                   for reason, count in sorted(ft_reasons.items())])

        ax.text(8.5, y_pos, ft_exclusion_text,
                ha='left', va='center', bbox=exclude_style, fontsize=9)

    # Arrow down to included
    ax.annotate('', xy=(5, y_pos - 1.5), xytext=(5, y_pos - 0.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='green'))

    # INCLUDED STAGE
    y_pos = 6.5
    ax.text(5, y_pos, f"Studies included in systematic review\n(n = {ft_included})",
            ha='center', va='center', bbox=include_style, fontsize=11, fontweight='bold')

    # PRISMA citation
    ax.text(5, 0.5,
            "PRISMA 2020 flow diagram template\n" +
            "Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement.\n" +
            "BMJ 2021;372:n71. doi: 10.1136/bmj.n71",
            ha='center', va='bottom', fontsize=7, style='italic', color='gray')

    # Metadata
    timestamp = prisma_data.get("generated_at", "Unknown")
    ax.text(0.2, 0.2, f"Generated: {timestamp}", ha='left', va='bottom',
            fontsize=7, color='gray')

    # Save
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✓ PRISMA flow diagram saved to: {output_path}")


def create_forest_plot(
    study_data: List[Dict],
    output_path: str,
    title: Optional[str] = "Forest Plot",
    effect_measure: str = "OR",
    dpi: int = 300
) -> None:
    """
    Generate a forest plot for meta-analysis results.

    Args:
        study_data: List of dicts with keys: study_name, effect_size, ci_lower, ci_upper, weight
        output_path: Path to save the PNG/PDF file
        title: Title for the plot
        effect_measure: Type of effect measure (OR, RR, MD, SMD)
        dpi: Resolution for the output image

    Note: This is a placeholder implementation. Full integration with Module 5
          (Meta-Analysis Agent) is required for production use.

    Example study_data format:
        [
            {"study_name": "Smith 2020", "effect_size": 0.85, "ci_lower": 0.70, "ci_upper": 1.02, "weight": 25.3},
            {"study_name": "Jones 2021", "effect_size": 0.92, "ci_lower": 0.78, "ci_upper": 1.08, "weight": 30.1},
            ...
        ]
    """
    if not HAS_MATPLOTLIB:
        raise RuntimeError("matplotlib is required for visualization. Install with: pip install matplotlib")

    if not study_data:
        raise ValueError("No study data provided for forest plot")

    n_studies = len(study_data)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, max(8, n_studies * 0.5 + 3)))

    # Y positions for studies (reversed so first study is at top)
    y_positions = list(range(n_studies, 0, -1))

    # Plot each study
    for i, study in enumerate(study_data):
        y = y_positions[i]
        effect = study["effect_size"]
        ci_low = study["ci_lower"]
        ci_high = study["ci_upper"]
        weight = study.get("weight", 1.0)

        # Horizontal CI line
        ax.plot([ci_low, ci_high], [y, y], 'k-', linewidth=1.5)

        # Square at effect size (size proportional to weight)
        marker_size = max(50, weight * 3)
        ax.scatter([effect], [y], s=marker_size, marker='s',
                  color='royalblue', edgecolors='black', linewidth=1.5, zorder=3)

        # Study name on left
        ax.text(-0.1, y, study["study_name"], ha='right', va='center', fontsize=10)

        # Effect size and CI on right
        ci_text = f"{effect:.2f} [{ci_low:.2f}, {ci_high:.2f}]"
        ax.text(ax.get_xlim()[1] + 0.1, y, ci_text, ha='left', va='center', fontsize=9)

    # Overall pooled effect (if provided)
    if any(study.get("is_pooled", False) for study in study_data):
        pooled = [s for s in study_data if s.get("is_pooled", False)][0]
        y_pooled = 0.5

        # Diamond for pooled effect
        effect = pooled["effect_size"]
        ci_low = pooled["ci_lower"]
        ci_high = pooled["ci_upper"]

        diamond_x = [ci_low, effect, ci_high, effect]
        diamond_y = [y_pooled, y_pooled + 0.2, y_pooled, y_pooled - 0.2]
        ax.fill(diamond_x, diamond_y, color='darkgreen', edgecolor='black', linewidth=2, zorder=4)

        ax.text(-0.1, y_pooled, "Overall (Random Effects)", ha='right', va='center',
               fontsize=11, fontweight='bold')
        ci_text = f"{effect:.2f} [{ci_low:.2f}, {ci_high:.2f}]"
        ax.text(ax.get_xlim()[1] + 0.1, y_pooled, ci_text, ha='left', va='center',
               fontsize=10, fontweight='bold')

    # Vertical line at null effect
    null_value = 1.0 if effect_measure in ["OR", "RR"] else 0.0
    ax.axvline(null_value, color='black', linestyle='--', linewidth=1.5, alpha=0.7)

    # Labels
    ax.set_xlabel(f"{effect_measure} (95% CI)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Study", fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    # Adjust limits
    ax.set_ylim(0, n_studies + 1)

    # Remove y-axis ticks
    ax.set_yticks([])

    # Grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Save
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✓ Forest plot saved to: {output_path}")


def check_dependencies() -> bool:
    """Check if visualization dependencies are installed."""
    return HAS_MATPLOTLIB


if __name__ == "__main__":
    # Test with dummy data
    if check_dependencies():
        print("✓ Visualization dependencies available")
    else:
        print("✗ Missing dependencies. Install with: pip install matplotlib")
