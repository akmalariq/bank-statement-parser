#!/usr/bin/env python3
"""
Multi-Bank Statement Parser
Runs all bank statement parsers and generates combined Excel reports
"""

import sys
from pathlib import Path

# Add parsers to path
sys.path.insert(0, str(Path(__file__).parent))

from parsers import casa_parser, bni_parser, span_parser


def main():
    """Run all parsers and generate reports."""
    project_dir = Path(__file__).parent
    excel_dir = project_dir / 'excel'
    excel_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🏦 Multi-Bank Statement Parser")
    print("=" * 60)
    
    results = []
    
    # 1. Parse CASA (CIMB/OCTO) statements
    print("\n" + "=" * 60)
    print("📁 CASA (CIMB/OCTO) Statements")
    print("=" * 60)
    
    casa_dir = project_dir / 'pdf' / 'casa'
    casa_output = excel_dir / 'CASA_Combined_Statements.xlsx'
    
    if casa_dir.exists() and list(casa_dir.glob('*.pdf*')):
        result = casa_parser.compile_all_pdfs(str(casa_dir), str(casa_output))
        if result:
            results.append(('CASA', result))
    else:
        print(f"  ⚠ No CASA PDFs found in {casa_dir}")
    
    # 2. Parse BNI statements
    print("\n" + "=" * 60)
    print("📁 BNI Statements")
    print("=" * 60)
    
    bni_dir = project_dir / 'pdf' / 'bni'
    bni_output = excel_dir / 'BNI_Combined_Statements.xlsx'
    
    if bni_dir.exists() and list(bni_dir.glob('BNI_*.pdf')):
        result = bni_parser.compile_bni_pdfs(str(bni_dir), str(bni_output))
        if result:
            results.append(('BNI', result))
    else:
        print(f"  ⚠ No BNI PDFs found in {bni_dir}")
    
    # 3. Parse SPAN (Government Treasury) statements
    print("\n" + "=" * 60)
    print("📁 SPAN (Government Treasury) Statements")
    print("=" * 60)
    
    span_dir = project_dir / 'pdf' / 'span'
    span_output = excel_dir / 'SPAN_Combined_Statements.xlsx'
    
    if span_dir.exists() and list(span_dir.glob('*.pdf')):
        result = span_parser.compile_span_pdfs(str(span_dir), str(span_output))
        if result:
            results.append(('SPAN', result))
    else:
        print(f"  ⚠ No SPAN PDFs found in {span_dir}")
    
    # 4. Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    if results:
        print("\n✅ Generated files:")
        for bank, path in results:
            print(f"   {bank}: {path}")
    else:
        print("\n❌ No files generated")
    
    return results


if __name__ == "__main__":
    main()

