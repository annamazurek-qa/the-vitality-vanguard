#!/usr/bin/env python3
"""
CLI: Generate PRISMA Flow Diagram and Forest Plots

This script generates publication-ready visualizations from screening results:
1. PRISMA flow diagram from PRISMA statistics JSON
2. Forest plot from meta-analysis results (optional, requires Module 5 data)

Usage:
    # Generate PRISMA flow diagram only
    python3 -m screening.cli.make_plots \\
        --prisma screening/out/prisma.json \\
        --output screening/out/prisma_flow.png

    # Generate both PRISMA and forest plot
    python3 -m screening.cli.make_plots \\
        --prisma screening/out/prisma.json \\
        --forest screening/out/meta_analysis.json \\
        --output-dir screening/out/plots/

Requirements:
    pip install matplotlib

Author: Screening Module (Module 3)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.visualizations import (
    create_prisma_flow_diagram,
    create_forest_plot,
    check_dependencies
)


def load_json(path: str) -> dict:
    """Load JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Generate PRISMA flow diagrams and forest plots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # PRISMA flow diagram only
    python3 -m screening.cli.make_plots \\
        --prisma out/prisma.json \\
        --output out/prisma_flow.png

    # With custom title and high resolution
    python3 -m screening.cli.make_plots \\
        --prisma out/prisma.json \\
        --output out/prisma_flow.png \\
        --title "Resveratrol & T2D Systematic Review" \\
        --dpi 600

    # Generate forest plot (requires meta-analysis data from Module 5)
    python3 -m screening.cli.make_plots \\
        --forest out/meta_analysis.json \\
        --output out/forest_plot.png \\
        --effect-measure OR
        """
    )

    parser.add_argument(
        "--prisma",
        type=str,
        help="Path to PRISMA statistics JSON (from make_prisma.py)"
    )

    parser.add_argument(
        "--forest",
        type=str,
        help="Path to meta-analysis results JSON (from Module 5)"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output path for single plot (e.g., prisma_flow.png)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for multiple plots (alternative to --output)"
    )

    parser.add_argument(
        "--title",
        type=str,
        help="Custom title for PRISMA diagram"
    )

    parser.add_argument(
        "--effect-measure",
        type=str,
        default="OR",
        choices=["OR", "RR", "MD", "SMD"],
        help="Effect measure for forest plot (default: OR)"
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Resolution (DPI) for output images (default: 300)"
    )

    parser.add_argument(
        "--format",
        type=str,
        default="png",
        choices=["png", "pdf", "svg"],
        help="Output format (default: png)"
    )

    args = parser.parse_args()

    # Check dependencies
    if not check_dependencies():
        print("Error: matplotlib is required for plot generation")
        print("Install with: pip install matplotlib")
        sys.exit(1)

    # Validate inputs
    if not args.prisma and not args.forest:
        print("Error: Must provide at least --prisma or --forest")
        parser.print_help()
        sys.exit(1)

    if not args.output and not args.output_dir:
        print("Error: Must provide either --output or --output-dir")
        parser.print_help()
        sys.exit(1)

    # Determine output paths
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        prisma_output = output_dir / f"prisma_flow.{args.format}"
        forest_output = output_dir / f"forest_plot.{args.format}"
    else:
        prisma_output = args.output
        forest_output = args.output.replace("prisma", "forest")

    # Generate PRISMA flow diagram
    if args.prisma:
        print(f"Loading PRISMA data from: {args.prisma}")
        prisma_data = load_json(args.prisma)

        print(f"Generating PRISMA flow diagram...")
        create_prisma_flow_diagram(
            prisma_data=prisma_data,
            output_path=str(prisma_output),
            title=args.title,
            dpi=args.dpi
        )

    # Generate forest plot
    if args.forest:
        print(f"Loading meta-analysis data from: {args.forest}")
        forest_data = load_json(args.forest)

        # Expected format: {"studies": [...], "pooled": {...}}
        if "studies" not in forest_data:
            print("Warning: Forest plot data missing 'studies' key")
            print("Expected format: {\"studies\": [...], \"pooled\": {...}}")
            sys.exit(1)

        study_data = forest_data["studies"]

        # Add pooled result if available
        if "pooled" in forest_data:
            pooled = forest_data["pooled"]
            pooled["is_pooled"] = True
            study_data.append(pooled)

        print(f"Generating forest plot with {len(study_data)} studies...")
        title = forest_data.get("title", f"Forest Plot ({args.effect_measure})")

        create_forest_plot(
            study_data=study_data,
            output_path=str(forest_output),
            title=title,
            effect_measure=args.effect_measure,
            dpi=args.dpi
        )

    print("\n" + "="*60)
    print("✓ Plot generation complete!")
    print("="*60)

    if args.prisma:
        print(f"PRISMA flow diagram: {prisma_output}")
    if args.forest:
        print(f"Forest plot: {forest_output}")


if __name__ == "__main__":
    main()
