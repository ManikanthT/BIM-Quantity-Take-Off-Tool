import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class CostEstimator:
    """
    Estimates project costs by applying unit rates to BOQ items.
    """
    
    def __init__(self, rates_path: Optional[str] = None):
        """
        Initialize the Cost Estimator.
        
        Args:
            rates_path: Path to the JSON file containing unit rates
        """
        self.rates = {}
        if rates_path:
            self.load_rates(rates_path)
            
    def load_rates(self, json_path: str) -> None:
        """Load rates from a JSON file."""
        try:
            with open(json_path, 'r') as f:
                self.rates = json.load(f)
            logger.info(f"Loaded rates from {json_path}")
        except Exception as e:
            logger.error(f"Failed to load rates from {json_path}: {e}")
            self.rates = {}

    def get_rate(self, element_type: str, material: str = None) -> float:
        """
        Get the unit rate for an element type and material.
        
        Priority:
        1. Specific material rate for the element type
        2. 'default' rate for the element type
        3. 0.0 if not found
        """
        type_rates = self.rates.get(element_type, {})
        
        if not type_rates:
            return 0.0
            
        # Try finding a rate that matches the material partially (case-insensitive)
        if material:
            material_lower = str(material).lower()
            for mat_key, rate in type_rates.items():
                if mat_key.lower() in material_lower and mat_key != 'default':
                    return rate
        
        # Fallback to default
        return type_rates.get('default', 0.0)

    def process_boq(self, input_path: str, output_path: str) -> None:
        """
        Read BOQ Excel, calculate costs, and write Priced BOQ.
        """
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        logger.info(f"Processing BOQ for cost estimation: {input_path}")
        
        try:
            xl = pd.ExcelFile(input_path)
        except Exception as e:
            logger.error(f"Failed to open Excel file: {e}")
            raise

        processed_dfs = {}
        summary_data = []

        # Process each BOQ sheet
        for sheet_name in xl.sheet_names:
            if sheet_name in ['Summary', 'Project Information', 'No Data']:
                continue
                
            try:
                df = pd.read_excel(input_path, sheet_name=sheet_name)
                
                if df.empty:
                    continue
                
                # Calculate costs
                rates = []
                total_costs = []
                
                for _, row in df.iterrows():
                    elem_type = row.get('element_type', '')
                    material = row.get('material', '')
                    quantity = pd.to_numeric(row.get('quantity', 0), errors='coerce')
                    
                    if pd.isna(quantity):
                        quantity = 0.0
                        
                    rate = self.get_rate(elem_type, material)
                    cost = quantity * rate
                    
                    rates.append(rate)
                    total_costs.append(cost)
                    
                    # Add to summary data
                    summary_data.append({
                        'Element Type': elem_type,
                        'Storey': row.get('storey', 'Unknown'),
                        'Material': material,
                        'Total Cost': cost
                    })
                
                # Add columns
                df['Rate'] = rates
                df['Total Cost'] = total_costs
                
                processed_dfs[sheet_name] = df
                
            except Exception as e:
                logger.warning(f"Error processing sheet {sheet_name}: {e}")

        # Generate Cost Summary
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            
            # Group by Element Type
            type_summary = summary_df.groupby('Element Type')['Total Cost'].sum().reset_index()
            type_summary.columns = ['Category', 'Total Cost']
            
            # Group by Storey
            storey_summary = summary_df.groupby('Storey')['Total Cost'].sum().reset_index()
            storey_summary.columns = ['Category', 'Total Cost']
            
            grand_total = summary_df['Total Cost'].sum()
            
            # Combine for final summary sheet
            final_summary = pd.concat([
                pd.DataFrame([{'Category': '--- BY ELEMENT TYPE ---', 'Total Cost': None}]),
                type_summary,
                pd.DataFrame([{'Category': '', 'Total Cost': None}]),
                pd.DataFrame([{'Category': '--- BY STOREY ---', 'Total Cost': None}]),
                storey_summary,
                pd.DataFrame([{'Category': '', 'Total Cost': None}]),
                pd.DataFrame([{'Category': 'GRAND TOTAL', 'Total Cost': grand_total}])
            ], ignore_index=True)
        else:
            final_summary = pd.DataFrame(columns=['Category', 'Total Cost'])

        # Write to Output (using existing ExcelExporter logic would be better, but we need to pass a dict of DFs)
        # For simplicity in this standalone module, we'll write directly using pandas/openpyxl
        # reusing the logic from ExcelExporter ideally, but here we'll do a custom write to handle the specific updates
        
        self._write_priced_boq(output_path, processed_dfs, final_summary, xl)

    def _write_priced_boq(self, output_path: str, dfs: Dict[str, pd.DataFrame], 
                          cost_summary: pd.DataFrame, original_xl: pd.ExcelFile) -> None:
        """Write the priced BOQ to Excel."""
        from src.excel_exporter import ExcelExporter
        
        # We can reuse the ExcelExporter for formatting if we instantiate it
        exporter = ExcelExporter(output_path)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write processed BOQ sheets
            for sheet_name, df in dfs.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
            # Write Cost Summary
            cost_summary.to_excel(writer, sheet_name='Cost Estimation', index=False)
            
            # Copy original Project Information if it exists
            if 'Project Information' in original_xl.sheet_names:
                pd.read_excel(original_xl, 'Project Information').to_excel(writer, sheet_name='Project Information', index=False)
                
            # Copy original Summary (quantities) if it exists
            if 'Summary' in original_xl.sheet_names:
                pd.read_excel(original_xl, 'Summary').to_excel(writer, sheet_name='Quantity Summary', index=False)
                
            # Apply formatting
            workbook = writer.book
            
            # Format BOQ sheets
            for sheet_name in dfs.keys():
                exporter._format_boq_sheet(workbook[sheet_name], dfs[sheet_name])
                
            # Format Cost Summary
            exporter._format_summary_sheet(workbook['Cost Estimation'])
