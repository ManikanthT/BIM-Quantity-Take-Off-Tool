"""
Main Entry Point for BIM QTO Tool
Command-line interface for processing IFC files and generating BOQs.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .ifc_reader import IFCReader
from .quantity_extractor import QuantityExtractor
from .boq_generator import BOQGenerator
from .boq_generator import BOQGenerator
from .excel_exporter import ExcelExporter
from .cost_estimator import CostEstimator


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def process_ifc_to_boq(
    ifc_path: str,
    output_path: str,
    grouping_level: str = 'type',
    cost_estimation: bool = False,
    rates_path: Optional[str] = None,
    verbose: bool = False
) -> bool:
    """
    Main processing function: Read IFC, extract quantities, generate BOQ, export to Excel.
    
    Args:
        ifc_path: Path to input IFC file
        output_path: Path for output Excel file
        grouping_level: How to group BOQ items ('type', 'storey', 'material', 'all')
        cost_estimation: Enable cost estimation
        rates_path: Path to rates JSON file (used if cost_estimation is True)
        verbose: Enable verbose logging
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Setup logging
        setup_logging(verbose)
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info("BIM Quantity Take-Off Tool - Starting Processing")
        logger.info("=" * 60)
        
        # Step 1: Read IFC file
        logger.info(f"\n[Step 1/5] Reading IFC file: {ifc_path}")
        ifc_reader = IFCReader(ifc_path)
        ifc_file = ifc_reader.get_file()
        
        # Get project information
        project_info = ifc_reader.get_project_info()
        logger.info(f"Project: {project_info.get('project_name', 'N/A')}")
        logger.info(f"Building: {project_info.get('building_name', 'N/A')}")
        logger.info(f"IFC Schema: {project_info.get('schema', 'N/A')}")
        
        # Step 2: Get civil engineering elements (Beam, Column, Slab, Wall, Footing)
        logger.info(f"\n[Step 2/5] Extracting civil engineering elements from IFC model...")
        elements = ifc_reader.get_civil_engineering_elements()
        logger.info(f"Found {len(elements)} civil engineering elements")
        
        if not elements:
            logger.warning("No civil engineering elements found in IFC file. BOQ will be empty.")
        
        # Step 3: Extract quantities with unit conversion
        logger.info(f"\n[Step 3/5] Extracting quantities from elements...")
        unit_scale_factor = project_info.get('unit_scale_factor', 0.001)
        logger.info(f"Unit conversion factor: {unit_scale_factor} (to meters)")
        
        extractor = QuantityExtractor(ifc_file, unit_scale_factor=unit_scale_factor)
        # Pass storey extraction function
        quantities = extractor.extract_all_quantities(
            elements, 
            get_storey_fn=ifc_reader.get_element_storey
        )
        logger.info(f"Successfully extracted quantities from {len(quantities)} elements")
        
        # Step 4: Generate BOQ
        logger.info(f"\n[Step 4/5] Generating Bill of Quantities (grouping: {grouping_level})...")
        boq_gen = BOQGenerator()
        boq_gen.load_quantities(quantities)
        boq_df = boq_gen.generate_boq(grouping_level=grouping_level)
        # Item numbers are added during BOQ generation or Excel export
        
        # Generate summary
        summary = boq_gen.get_summary(boq_df)
        logger.info(f"Generated BOQ with {summary.get('total_items', 0)} items")
        if summary.get('total_volume_m3', 0) > 0:
            logger.info(f"  Total Volume: {summary['total_volume_m3']:.2f} m³")
        if summary.get('total_area_m2', 0) > 0:
            logger.info(f"  Total Area: {summary['total_area_m2']:.2f} m²")
        if summary.get('total_length_m', 0) > 0:
            logger.info(f"  Total Length: {summary['total_length_m']:.2f} m")
        if summary.get('total_count', 0) > 0:
            logger.info(f"  Total Count: {summary['total_count']}")
        
        # Step 5: Export to Excel
        logger.info(f"\n[Step 5/5] Exporting BOQ to Excel: {output_path}")
        exporter = ExcelExporter(output_path)
        exporter.export_boq(boq_df, summary=summary, project_info=project_info)
        
        # Step 6: Cost Estimation (if enabled)
        if cost_estimation:
            logger.info(f"\n[Step 6/6] Calculating Project Costs...")
            try:
                # Initialize estimator
                estimator = CostEstimator(rates_path)
                
                # We need to process the file we just created
                # Note: Ideally we would pass the data directly, but CostEstimator is currently designed 
                # to read the Excel to preserve the flow. For tight integration, we could refactor.
                # For now, we'll use the process_boq method which reads/writes the file.
                
                # We overwrite the output file with the priced version
                estimator.process_boq(output_path, output_path)
                logger.info(f"Cost estimation completed and added to: {output_path}")
                
            except Exception as e:
                logger.error(f"Cost estimation failed: {e}")
                # Don't fail the whole process if only cost estimation fails
                logger.warning("Continuing without cost estimation results.")
        
        logger.info("\n" + "=" * 60)
        logger.info("Processing completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return False
    except ValueError as e:
        logger.error(f"Invalid IFC file: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='BIM Quantity Take-Off Tool - Extract quantities from IFC files and generate BOQs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m src.main input.ifc output.xlsx
  
  # With custom grouping
  python -m src.main input.ifc output.xlsx --grouping material
  
  # Verbose output
  python -m src.main input.ifc output.xlsx --verbose
        """
    )
    
    parser.add_argument(
        'ifc_file',
        type=str,
        help='Path to input IFC file'
    )
    
    parser.add_argument(
        'output_file',
        type=str,
        help='Path to output Excel file'
    )
    
    parser.add_argument(
        '--grouping',
        type=str,
        choices=['type', 'storey', 'material', 'all'],
        default='type',
        help='Grouping level for BOQ items (default: type). Options: type, storey, material, all'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--cost',
        action='store_true',
        help='Enable basic cost estimation'
    )
    
    parser.add_argument(
        '--rates',
        type=str,
        default='rates.json',
        help='Path to rates JSON file (default: rates.json)'
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    ifc_path = Path(args.ifc_file)
    if not ifc_path.exists():
        print(f"Error: IFC file not found: {args.ifc_file}", file=sys.stderr)
        sys.exit(1)
    
    # Process the IFC file
    success = process_ifc_to_boq(
        ifc_path=str(ifc_path),
        output_path=args.output_file,
        grouping_level=args.grouping,
        cost_estimation=args.cost,
        rates_path=args.rates,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
