"""
Bill of Quantities (BOQ) Generator Module
Organizes and summarizes extracted quantities into a structured BOQ.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import pandas as pd

logger = logging.getLogger(__name__)


class BOQGenerator:
    """
    Generates structured Bill of Quantities from extracted element quantities.
    
    Organizes quantities by category, type, and material for professional
    BOQ generation suitable for civil engineering projects.
    """
    
    def __init__(self):
        """Initialize the BOQ generator."""
        self.quantities: List[Dict[str, Any]] = []
        self.boq_items: List[Dict[str, Any]] = []
    
    def load_quantities(self, quantities: List[Dict[str, Any]]) -> None:
        """
        Load extracted quantities for BOQ generation.
        
        Args:
            quantities: List of quantity dictionaries from QuantityExtractor
        """
        self.quantities = quantities
        logger.info(f"Loaded {len(quantities)} quantity items for BOQ generation")
    
    def generate_boq(self, grouping_level: str = 'type') -> pd.DataFrame:
        """
        Generate a structured BOQ DataFrame.
        
        Args:
            grouping_level: How to group items ('type', 'storey', 'material', 'all')
                           - 'type': Group by element type
                           - 'storey': Group by building storey
                           - 'material': Group by material
                           - 'all': Group by element type, storey, and material
            
        Returns:
            DataFrame containing the BOQ with columns:
            Item No, Element Type, Description, Unit, Quantity, Storey, Material
        """
        if not self.quantities:
            logger.warning("No quantities loaded. Returning empty BOQ.")
            return pd.DataFrame()
        
        # Group quantities based on grouping level
        grouped = self._group_quantities(grouping_level)
        
        # Generate BOQ items
        self.boq_items = []
        for group_key, items in grouped.items():
            boq_item = self._create_boq_item(group_key, items, grouping_level)
            self.boq_items.append(boq_item)
        
        # Create DataFrame
        df = pd.DataFrame(self.boq_items)
        
        # Reorder columns to match requirements: Item No, Element Type, Description, Unit, Quantity, Storey, Material
        column_order = ['item_no', 'element_type', 'description', 'unit', 'quantity', 'storey', 'material']
        # Only include columns that exist
        available_columns = [col for col in column_order if col in df.columns]
        # Add any additional columns at the end
        remaining_columns = [col for col in df.columns if col not in available_columns]
        df = df[available_columns + remaining_columns]
        
        # Sort by element type and storey
        sort_columns = []
        if 'element_type' in df.columns:
            sort_columns.append('element_type')
        if 'storey' in df.columns:
            sort_columns.append('storey')
        if sort_columns:
            df = df.sort_values(by=sort_columns, ignore_index=True)
        
        logger.info(f"Generated BOQ with {len(df)} items")
        return df
    
    def _group_quantities(self, grouping_level: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group quantities based on the specified level.
        
        Args:
            grouping_level: Grouping strategy ('type', 'storey', 'material', 'all')
            
        Returns:
            Dictionary mapping group keys to lists of quantity items
        """
        grouped = defaultdict(list)
        
        for qty in self.quantities:
            if grouping_level == 'type':
                key = qty.get('type', 'Unknown')
            elif grouping_level == 'storey':
                storey = qty.get('storey', 'Unknown') or 'Unknown'
                key = storey
            elif grouping_level == 'material':
                key = qty.get('material', 'Unknown') or 'Unknown'
            elif grouping_level == 'all':
                # Group by element type, storey, and material combination
                typ = qty.get('type', 'Unknown')
                storey = qty.get('storey', 'Unknown') or 'Unknown'
                mat = qty.get('material', 'Unknown') or 'Unknown'
                key = f"{typ}|{storey}|{mat}"
            else:
                # Default to type grouping
                key = qty.get('type', 'Unknown')
            
            grouped[key].append(qty)
        
        return dict(grouped)
    
    def _create_boq_item(self, group_key: str, items: List[Dict[str, Any]], grouping_level: str) -> Dict[str, Any]:
        """
        Create a BOQ item from a group of quantity items.
        
        Args:
            group_key: The grouping key
            items: List of quantity items in this group
            grouping_level: The grouping level used
            
        Returns:
            BOQ item dictionary with required columns
        """
        # Extract element type, storey, material from first item or group key
        if '|' in group_key:
            # This is a composite key from 'all' grouping: type|storey|material
            parts = group_key.split('|')
            element_type = parts[0] if len(parts) > 0 else 'Unknown'
            storey = parts[1] if len(parts) > 1 else 'Unknown'
            material = parts[2] if len(parts) > 2 else 'Unknown'
        else:
            # Use first item as reference
            first_item = items[0]
            element_type = first_item.get('type', 'Unknown')
            storey = first_item.get('storey', None) or 'Not Specified'
            material = first_item.get('material', None) or 'Not Specified'
            
            # If grouping by storey, get storey from group_key
            if grouping_level == 'storey':
                storey = group_key if group_key != 'Unknown' else 'Not Specified'
        
        # Aggregate quantities
        total_volume = sum(item.get('volume', 0) or 0 for item in items)
        total_area = sum(item.get('area', 0) or 0 for item in items)
        total_length = sum(item.get('length', 0) or 0 for item in items)
        total_count = sum(item.get('count', 1) for item in items)
        
        # Create description
        description = self._create_description(element_type, material)
        
        # Determine unit of measurement
        unit, quantity = self._determine_primary_quantity(
            total_volume, total_area, total_length, total_count, element_type
        )
        
        # Create BOQ item with required columns
        boq_item = {
            'item_no': None,  # Will be assigned later
            'element_type': element_type,
            'description': description,
            'unit': unit,
            'quantity': round(quantity, 3),
            'storey': storey,
            'material': material,
            # Additional columns for reference
            'volume_m3': round(total_volume, 3) if total_volume > 0 else None,
            'area_m2': round(total_area, 3) if total_area > 0 else None,
            'length_m': round(total_length, 3) if total_length > 0 else None,
            'count': int(total_count),
        }
        
        return boq_item
    
    def _create_description(self, element_type: str, material: str) -> str:
        """
        Create a professional description for the BOQ item.
        
        Args:
            element_type: IFC element type
            material: Material name
            
        Returns:
            Formatted description string
        """
        # Clean up element type name (remove 'Ifc' prefix)
        type_name = element_type.replace('Ifc', '') if element_type.startswith('Ifc') else element_type
        
        if material and material not in ['Unknown', 'Not Specified', None]:
            return f"{type_name} - {material}"
        else:
            return type_name
    
    def _determine_primary_quantity(
        self, volume: float, area: float, length: float, count: int, element_type: str
    ) -> Tuple[str, float]:
        """
        Determine the primary unit and quantity based on element type and available data.
        
        Args:
            volume: Total volume in m³
            area: Total area in m²
            length: Total length in m
            count: Total count
            element_type: IFC element type
            
        Returns:
            Tuple of (unit, quantity)
        """
        # Element types that typically use volume
        volume_elements = ['IfcWall', 'IfcSlab', 'IfcFooting', 'IfcColumn', 'IfcBeam']
        # Element types that typically use area
        area_elements = ['IfcRoof', 'IfcCurtainWall', 'IfcRailing']
        # Element types that typically use length
        length_elements = ['IfcBeam', 'IfcPile']
        
        element_base = element_type.split('_')[0]
        
        # Prioritize based on element type and available data
        if element_base in volume_elements and volume > 0:
            return ('m³', volume)
        elif element_base in area_elements and area > 0:
            return ('m²', area)
        elif element_base in length_elements and length > 0:
            return ('m', length)
        elif volume > 0:
            return ('m³', volume)
        elif area > 0:
            return ('m²', area)
        elif length > 0:
            return ('m', length)
        else:
            return ('No.', count)
    
    def add_item_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add sequential item numbers to the BOQ DataFrame.
        
        Args:
            df: BOQ DataFrame
            
        Returns:
            DataFrame with item numbers added
        """
        if df.empty:
            return df
        
        df = df.copy()
        df.insert(0, 'item_no', range(1, len(df) + 1))
        return df
    
    def get_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a summary of the BOQ.
        
        Args:
            df: BOQ DataFrame
            
        Returns:
            Dictionary containing BOQ summary statistics
        """
        if df.empty:
            return {}
        
        summary = {
            'total_items': len(df),
            'total_volume_m3': df['volume_m3'].sum() if 'volume_m3' in df.columns else 0,
            'total_area_m2': df['area_m2'].sum() if 'area_m2' in df.columns else 0,
            'total_length_m': df['length_m'].sum() if 'length_m' in df.columns else 0,
            'total_count': df['count'].sum() if 'count' in df.columns else 0,
            'element_types': df['element_type'].unique().tolist() if 'element_type' in df.columns else [],
        }
        
        return summary
