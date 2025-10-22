#!/usr/bin/env python3
"""
The Vitality Vanguard - Complete Meta-Analysis Pipeline
========================================================

Automated systematic review and meta-analysis pipeline from research question to publication-ready results.

Usage:
    python3 pipeline.py --question "Your research question" --output results/

    # Or use an existing protocol:
    python3 pipeline.py --protocol protocol.json --output results/

Modules:
    1. Protocol & PICO Formulation (PrePico.py)
    2. Search Agent (search_agent.py)
    3. Screening & Selection (screening/)
    4. Data Extraction (extractor.py)
    5. Meta-Analysis & Visualization (meta_analyzer.py)

Author: The Vitality Vanguard Team
Challenge: HackAging.AI - Future of Evidence
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Module imports
try:
    from PrePico import PICOExtractor
    from search_agent import build_query, search_pubmed, fetch_metadata
    from extractor import PDFLLMExtractor
    from meta_analyzer import (
        load_jsons,
        build_study_rows,
        pool_fixed_inv_var,
        make_forest
    )
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required modules are in the current directory.")
    sys.exit(1)


class MetaAnalysisPipeline:
    """
    Complete automated meta-analysis pipeline orchestrator.
    """

    def __init__(self, output_dir: str = "results", debug: bool = False):
        """
        Initialize pipeline.

        Args:
            output_dir: Directory for all output files
            debug: Enable debug logging
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.debug = debug

        # Create subdirectories
        self.protocol_dir = self.output_dir / "1_protocol"
        self.search_dir = self.output_dir / "2_search"
        self.screening_dir = self.output_dir / "3_screening"
        self.extraction_dir = self.output_dir / "4_extraction"
        self.analysis_dir = self.output_dir / "5_analysis"

        for d in [self.protocol_dir, self.search_dir, self.screening_dir,
                  self.extraction_dir, self.analysis_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.log_file = self.output_dir / "pipeline.log"
        self.start_time = time.time()

        self.log("="*70)
        self.log("THE VITALITY VANGUARD - META-ANALYSIS PIPELINE")
        self.log("="*70)
        self.log(f"Started at: {datetime.now().isoformat()}")
        self.log(f"Output directory: {self.output_dir.absolute()}")
        self.log("")

    def log(self, message: str):
        """Log message to console and file."""
        print(message)
        with open(self.log_file, 'a') as f:
            f.write(f"{message}\n")

    def step(self, step_num: int, description: str):
        """Log a pipeline step."""
        self.log("")
        self.log(f"{'='*70}")
        self.log(f"STEP {step_num}: {description}")
        self.log(f"{'='*70}")

    def run_module_1_protocol(self, question: str = None, protocol_path: str = None) -> Dict:
        """
        MODULE 1: Protocol & PICO Formulation

        Args:
            question: Research question (if creating new protocol)
            protocol_path: Path to existing protocol JSON

        Returns:
            Protocol dictionary
        """
        self.step(1, "Protocol & PICO Formulation")

        if protocol_path and os.path.exists(protocol_path):
            self.log(f"Loading existing protocol from: {protocol_path}")
            with open(protocol_path, 'r') as f:
                protocol = json.load(f)

            # Save copy to output
            output_path = self.protocol_dir / "protocol.json"
            with open(output_path, 'w') as f:
                json.dump(protocol, f, indent=2)

            self.log(f"✓ Protocol loaded and saved to: {output_path}")
            return protocol

        if not question:
            raise ValueError("Must provide either --question or --protocol")

        self.log(f"Research question: {question}")
        self.log("Extracting PICO elements...")

        # Initialize PICO extractor
        extractor = PICOExtractor()
        pico_result = extractor.extract_pico(question)

        # Build protocol structure
        protocol = {
            "protocol_id": f"vv_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": question,
            "created_date": datetime.now().isoformat(),
            "pico": {
                "population": pico_result.get("population", ""),
                "intervention": pico_result.get("intervention", ""),
                "comparison": pico_result.get("comparison", ""),
                "outcomes": pico_result.get("outcomes", [])
            },
            "keywords": self._generate_keywords(pico_result),
            "inclusion_criteria": [
                "Original research articles (RCTs, cohort, case-control)",
                "Human participants",
                "Published 2000-present",
                "English language",
                "Full text available"
            ],
            "exclusion_criteria": [
                "Animal-only studies",
                "In vitro studies",
                "Reviews and meta-analyses",
                "Case reports"
            ]
        }

        # Save protocol
        output_path = self.protocol_dir / "protocol.json"
        with open(output_path, 'w') as f:
            json.dump(protocol, f, indent=2)

        self.log(f"✓ Protocol created and saved to: {output_path}")
        self.log(f"  Population: {protocol['pico']['population']}")
        self.log(f"  Intervention: {protocol['pico']['intervention']}")
        self.log(f"  Comparison: {protocol['pico']['comparison']}")
        self.log(f"  Outcomes: {', '.join(protocol['pico']['outcomes'])}")

        return protocol

    def _generate_keywords(self, pico_result: Dict) -> Dict:
        """Generate search keywords from PICO elements."""
        # Simple keyword extraction (can be enhanced)
        return {
            "population_terms": self._extract_keywords(pico_result.get("population", "")),
            "intervention_terms": self._extract_keywords(pico_result.get("intervention", "")),
            "outcome_terms": self._extract_keywords(pico_result.get("outcomes", []))
        }

    def _extract_keywords(self, text) -> List[str]:
        """Extract keywords from text."""
        if isinstance(text, list):
            return [str(item) for item in text]

        # Basic keyword extraction (split on common separators)
        import re
        words = re.split(r'[,;\s]+', str(text).lower())
        # Filter common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        keywords = [w.strip() for w in words if w.strip() and w.strip() not in stopwords]
        return keywords[:10]  # Limit to top 10

    def run_module_2_search(self, protocol: Dict, max_results: int = 1000) -> List[str]:
        """
        MODULE 2: Systematic Search

        Args:
            protocol: Protocol dictionary with search terms
            max_results: Maximum results per database

        Returns:
            List of PMIDs
        """
        self.step(2, "Systematic Search & Retrieval")

        # Build search query
        query = build_query(protocol)
        self.log(f"Search query: {query}")

        # Search PubMed
        self.log("Searching PubMed...")
        pmids, count = search_pubmed(query, retmax=max_results)
        self.log(f"✓ Found {count} results, retrieved {len(pmids)} PMIDs")

        # Fetch metadata
        self.log("Fetching article metadata...")
        metadata_list = fetch_metadata(pmids)

        # Save citations
        citations_path = self.search_dir / "citations.jsonl"
        with open(citations_path, 'w') as f:
            for meta in metadata_list:
                f.write(json.dumps(meta) + '\n')

        self.log(f"✓ Saved {len(metadata_list)} citations to: {citations_path}")

        return pmids

    def run_module_3_screening(self, protocol: Dict) -> List[str]:
        """
        MODULE 3: Screening & Selection

        Args:
            protocol: Protocol dictionary

        Returns:
            List of included study IDs
        """
        self.step(3, "Screening & Selection")

        # Copy protocol to screening data directory
        import shutil
        protocol_path = self.protocol_dir / "protocol.json"
        screening_protocol = Path("screening/data/protocol.json")
        screening_protocol.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(protocol_path, screening_protocol)

        # Copy citations
        citations_src = self.search_dir / "citations.jsonl"
        citations_dst = Path("screening/data/citations.jsonl")
        if citations_src.exists():
            shutil.copy(citations_src, citations_dst)

        self.log("Running Title/Abstract screening...")
        import subprocess

        # Run TA screening
        result = subprocess.run([
            "python3", "-m", "screening.cli.ta_screen",
            "--citations", "screening/data/citations.jsonl",
            "--protocol", "screening/data/protocol.json",
            "--decisions", "screening/out/ta_decisions.jsonl",
            "--classifications", "screening/out/classifications.jsonl",
            "--topic", "resveratrol_t2d"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            self.log(f"Warning: TA screening returned code {result.returncode}")
            if result.stderr:
                self.log(f"Error: {result.stderr}")

        # Run FT screening
        self.log("Running Full-Text screening...")
        result = subprocess.run([
            "python3", "-m", "screening.cli.ft_screen",
            "--ta", "screening/out/ta_decisions.jsonl",
            "--protocol", "screening/data/protocol.json",
            "--decisions", "screening/out/ft_decisions.jsonl"
        ], capture_output=True, text=True)

        # Generate PRISMA
        self.log("Generating PRISMA statistics...")
        result = subprocess.run([
            "python3", "-m", "screening.cli.make_prisma",
            "--ta", "screening/out/ta_decisions.jsonl",
            "--ft", "screening/out/ft_decisions.jsonl",
            "--out", "screening/out/prisma.json"
        ], capture_output=True, text=True)

        # Generate PRISMA flow diagram
        self.log("Generating PRISMA flow diagram...")
        result = subprocess.run([
            "python3", "-m", "screening.cli.make_plots",
            "--prisma", "screening/out/prisma.json",
            "--output", str(self.screening_dir / "prisma_flow.png"),
            "--title", protocol.get("title", "Systematic Review"),
            "--dpi", "300"
        ], capture_output=True, text=True)

        # Copy outputs
        for file in ["ta_decisions.jsonl", "ft_decisions.jsonl", "prisma.json", "classifications.jsonl"]:
            src = Path(f"screening/out/{file}")
            if src.exists():
                shutil.copy(src, self.screening_dir / file)

        # Extract included study IDs
        included_ids = []
        ft_decisions = self.screening_dir / "ft_decisions.jsonl"
        if ft_decisions.exists():
            with open(ft_decisions) as f:
                for line in f:
                    record = json.loads(line)
                    if record.get("decision") == "include":
                        included_ids.append(record["id"])

        self.log(f"✓ Screening complete: {len(included_ids)} studies included")

        return included_ids

    def run_module_4_extraction(self, included_ids: List[str], question: str) -> List[str]:
        """
        MODULE 4: Data Extraction

        Args:
            included_ids: List of included study IDs
            question: Research question for extraction

        Returns:
            List of extraction JSON file paths
        """
        self.step(4, "Data Extraction")

        self.log(f"Extracting data from {len(included_ids)} studies...")
        self.log("NOTE: This requires PDF files in ./pdfs/ directory")

        # Initialize extractor
        extractor = PDFLLMExtractor(debug=self.debug)

        extraction_files = []
        pdf_dir = Path("pdfs")

        if not pdf_dir.exists():
            self.log("Warning: pdfs/ directory not found. Skipping extraction.")
            return []

        for study_id in included_ids:
            # Find PDF file
            pdf_files = list(pdf_dir.glob(f"*{study_id}*.pdf"))
            if not pdf_files:
                self.log(f"  Warning: No PDF found for {study_id}")
                continue

            pdf_path = pdf_files[0]
            self.log(f"  Processing: {pdf_path.name}")

            try:
                # Extract data
                result = extractor.extract_from_pdf(str(pdf_path), question)

                # Save extraction
                output_file = self.extraction_dir / f"{study_id}.json"
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)

                extraction_files.append(str(output_file))
                self.log(f"    ✓ Saved to: {output_file.name}")

            except Exception as e:
                self.log(f"    ✗ Error: {str(e)}")

        self.log(f"✓ Extraction complete: {len(extraction_files)} files")

        return extraction_files

    def run_module_5_analysis(self, extraction_dir: Path) -> Dict:
        """
        MODULE 5: Meta-Analysis & Visualization

        Args:
            extraction_dir: Directory containing extraction JSONs

        Returns:
            Analysis results dictionary
        """
        self.step(5, "Meta-Analysis & Statistical Synthesis")

        # Load all extraction JSONs
        json_files = list(extraction_dir.glob("*.json"))
        if not json_files:
            self.log("Warning: No extraction files found. Skipping analysis.")
            return {}

        self.log(f"Loading {len(json_files)} extraction files...")
        studies = load_jsons([str(f) for f in json_files])

        # Build study rows
        self.log("Building study data rows...")
        rows = build_study_rows(studies)

        if not rows:
            self.log("Warning: No valid study data extracted.")
            return {}

        # Pool by outcome and effect type
        self.log("Performing meta-analysis...")
        results = {}

        import pandas as pd
        df = pd.DataFrame(rows)

        # Group by outcome and type
        for (outcome, etype), grp in df.groupby(['outcome', 'type']):
            if len(grp) < 2:
                self.log(f"  Skipping {outcome} ({etype}): only {len(grp)} study")
                continue

            self.log(f"  Analyzing {outcome} ({etype}): {len(grp)} studies")

            # Perform fixed-effect meta-analysis
            pooled_result = pool_fixed_inv_var(grp)
            results[f"{outcome}_{etype}"] = pooled_result

            # Generate forest plot
            plot_path = self.analysis_dir / f"forest_{outcome}_{etype}.png"
            make_forest(grp, pooled_result, str(plot_path),
                       title=f"{outcome} ({etype})")

            self.log(f"    Pooled effect: {pooled_result['pooled_effect']:.3f} "
                    f"[{pooled_result['ci_lower']:.3f}, {pooled_result['ci_upper']:.3f}]")
            self.log(f"    Forest plot saved: {plot_path.name}")

        # Save results summary
        summary_path = self.analysis_dir / "meta_analysis_results.json"
        with open(summary_path, 'w') as f:
            json.dump(results, f, indent=2)

        self.log(f"✓ Meta-analysis complete: {len(results)} outcomes analyzed")
        self.log(f"  Results saved to: {summary_path}")

        return results

    def generate_final_report(self, protocol: Dict, results: Dict):
        """Generate final summary report."""
        self.step(6, "Final Report Generation")

        report_path = self.output_dir / "FINAL_REPORT.md"

        elapsed = time.time() - self.start_time

        with open(report_path, 'w') as f:
            f.write("# Meta-Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Pipeline Runtime:** {elapsed:.1f} seconds\n\n")

            f.write("## Research Question\n\n")
            f.write(f"{protocol.get('title', 'N/A')}\n\n")

            f.write("## PICO Framework\n\n")
            pico = protocol.get('pico', {})
            f.write(f"- **Population:** {pico.get('population', 'N/A')}\n")
            f.write(f"- **Intervention:** {pico.get('intervention', 'N/A')}\n")
            f.write(f"- **Comparison:** {pico.get('comparison', 'N/A')}\n")
            f.write(f"- **Outcomes:** {', '.join(pico.get('outcomes', []))}\n\n")

            f.write("## Results Summary\n\n")
            for outcome_key, result in results.items():
                f.write(f"### {outcome_key}\n\n")
                f.write(f"- Pooled Effect: {result.get('pooled_effect', 'N/A'):.3f}\n")
                f.write(f"- 95% CI: [{result.get('ci_lower', 'N/A'):.3f}, {result.get('ci_upper', 'N/A'):.3f}]\n")
                f.write(f"- Number of Studies: {result.get('k', 'N/A')}\n")
                f.write(f"- Heterogeneity (I²): {result.get('i_squared', 0):.1f}%\n\n")

            f.write("## Output Files\n\n")
            f.write(f"- Protocol: `{self.protocol_dir}/protocol.json`\n")
            f.write(f"- Search Results: `{self.search_dir}/citations.jsonl`\n")
            f.write(f"- Screening Results: `{self.screening_dir}/ft_decisions.jsonl`\n")
            f.write(f"- PRISMA Diagram: `{self.screening_dir}/prisma_flow.png`\n")
            f.write(f"- Extracted Data: `{self.extraction_dir}/`\n")
            f.write(f"- Forest Plots: `{self.analysis_dir}/forest_*.png`\n")

        self.log(f"✓ Final report saved to: {report_path}")

        self.log("")
        self.log("="*70)
        self.log("PIPELINE COMPLETE")
        self.log("="*70)
        self.log(f"Total runtime: {elapsed:.1f} seconds")
        self.log(f"All outputs saved to: {self.output_dir.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="The Vitality Vanguard - Automated Meta-Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Start with a research question
    python3 pipeline.py --question "Does resveratrol improve glycemic control in T2D?"

    # Use existing protocol
    python3 pipeline.py --protocol protocol.json

    # Specify output directory
    python3 pipeline.py --protocol protocol.json --output results_2025/

    # Enable debug mode
    python3 pipeline.py --protocol protocol.json --debug
        """
    )

    parser.add_argument(
        "--question",
        type=str,
        help="Research question for meta-analysis"
    )

    parser.add_argument(
        "--protocol",
        type=str,
        help="Path to existing protocol JSON file"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="results",
        help="Output directory for all results (default: results/)"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=1000,
        help="Maximum search results to retrieve (default: 1000)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    if not args.question and not args.protocol:
        parser.error("Must provide either --question or --protocol")

    # Initialize pipeline
    pipeline = MetaAnalysisPipeline(
        output_dir=args.output,
        debug=args.debug
    )

    try:
        # Run all modules
        protocol = pipeline.run_module_1_protocol(
            question=args.question,
            protocol_path=args.protocol
        )

        pmids = pipeline.run_module_2_search(
            protocol=protocol,
            max_results=args.max_results
        )

        included_ids = pipeline.run_module_3_screening(protocol=protocol)

        extraction_files = pipeline.run_module_4_extraction(
            included_ids=included_ids,
            question=protocol.get('title', '')
        )

        results = pipeline.run_module_5_analysis(
            extraction_dir=pipeline.extraction_dir
        )

        pipeline.generate_final_report(protocol=protocol, results=results)

    except Exception as e:
        pipeline.log(f"\n✗ ERROR: {str(e)}")
        if args.debug:
            import traceback
            pipeline.log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
