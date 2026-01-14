"""
Example Usage Script
Demonstrates how to use the BIM QTO tool programmatically.
"""

from src.ifc_reader import IFCReader
from src.quantity_extractor import QuantityExtractor
from src.boq_generator import BOQGenerator
from src.excel_exporter import ExcelExporter
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def example_basic_usage():
    """Basic example of processing an IFC file."""
    
    # Input file (change this to your IFC file path)
    ifc_file_path = "example_model.ifc"
    output_excel_path = "boq_output.xlsx"
    
    try:
        # Step 1: Read IFC file
        print("Reading IFC file...")
        reader = IFCReader(ifc_file_path)
        ifc_file = reader.get_file()
        project_info = reader.get_project_info()
        
        print(f"Project: {project_info.get('project_name', 'N/A')}")
        print(f"IFC Schema: {project_info.get('schema', 'N/A')}")
        
        # Step 2: Get building elements
        print("\nExtracting building elements...")
        elements = reader.get_all_building_elements()
        print(f"Found {len(elements)} building elements")
        
        # Step 3: Extract quantities
        print("\nExtracting quantities...")
        extractor = QuantityExtractor(ifc_file)
        quantities = extractor.extract_all_quantities(elements)
        print(f"Extracted quantities from {len(quantities)} elements")
        
        # Step 4: Generate BOQ
        print("\nGenerating BOQ...")
        boq_gen = BOQGenerator()
        boq_gen.load_quantities(quantities)
        
        # Try different grouping levels
        for grouping in ['category', 'type', 'material']:
            print(f"\n  Generating BOQ with grouping: {grouping}")
            boq_df = boq_gen.generate_boq(grouping_level=grouping)
            boq_df = boq_gen.add_item_numbers(boq_df)
            summary = boq_gen.get_summary(boq_df)
            
            print(f"    Items: {summary.get('total_items', 0)}")
            if summary.get('total_volume_m3', 0) > 0:
                print(f"    Total Volume: {summary['total_volume_m3']:.2f} m³")
        
        # Step 5: Export to Excel (using category grouping)
        print(f"\nExporting to Excel: {output_excel_path}")
        boq_df = boq_gen.generate_boq(grouping_level='category')
        boq_df = boq_gen.add_item_numbers(boq_df)
        summary = boq_gen.get_summary(boq_df)
        
        exporter = ExcelExporter(output_excel_path)
        exporter.export_boq(boq_df, summary=summary, project_info=project_info)
        
        print("\n✓ Processing completed successfully!")
        print(f"✓ BOQ saved to: {output_excel_path}")
        
    except FileNotFoundError:
        print(f"Error: IFC file not found: {ifc_file_path}")
        print("Please update the 'ifc_file_path' variable with a valid IFC file path.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def example_custom_filtering():
    """Example of filtering specific element types."""
    
    ifc_file_path = "example_model.ifc"
    
    try:
        reader = IFCReader(ifc_file_path)
        ifc_file = reader.get_file()
        
        # Get only walls and slabs
        print("Extracting walls and slabs only...")
        walls = reader.get_elements_by_type('IfcWall')
        slabs = reader.get_elements_by_type('IfcSlab')
        
        elements = walls + slabs
        print(f"Found {len(elements)} elements (walls: {len(walls)}, slabs: {len(slabs)})")
        
        # Extract quantities
        extractor = QuantityExtractor(ifc_file)
        quantities = extractor.extract_all_quantities(elements)
        
        # Generate BOQ
        boq_gen = BOQGenerator()
        boq_gen.load_quantities(quantities)
        boq_df = boq_gen.generate_boq(grouping_level='type')
        boq_df = boq_gen.add_item_numbers(boq_df)
        
        print("\nFiltered BOQ:")
        print(boq_df[['item_no', 'element_type', 'quantity', 'unit', 'volume_m3']].to_string())
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("BIM QTO Tool - Example Usage")
    print("=" * 60)
    print("\nNote: Update the 'ifc_file_path' variable with your IFC file path")
    print("\nRunning basic usage example...\n")
    
    example_basic_usage()
    
    # Uncomment to run custom filtering example
    # print("\n" + "=" * 60)
    # example_custom_filtering()
