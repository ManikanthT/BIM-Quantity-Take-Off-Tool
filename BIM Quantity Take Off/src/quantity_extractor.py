"""
Quantity Extraction Module
Extracts quantities (volume, area, length, count) from IFC elements.
"""

import logging
from typing import Dict, List, Optional, Any
import ifcopenshell
from ifcopenshell import geom

logger = logging.getLogger(__name__)


class QuantityExtractor:
    """
    Extracts quantities from IFC building elements.
    
    This class handles both Qto properties and geometric calculations
    to extract volumes, areas, lengths, and counts for BOQ generation.
    """
    
    def __init__(self, ifc_file: Any, unit_scale_factor: float = 0.001):
        """
        Initialize the quantity extractor.
        
        Args:
            ifc_file: The ifcopenshell file object
            unit_scale_factor: Factor to convert IFC units to meters (default: 0.001 for mm to m)
        """
        self.ifc_file = ifc_file
        self.unit_scale_factor = unit_scale_factor
        self.settings = ifcopenshell.geom.settings()
        self.settings.set(self.settings.USE_WORLD_COORDS, True)
    
    def extract_quantities(self, element: Any, storey: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract all relevant quantities from an IFC element.
        
        Prioritizes IfcElementQuantity/IfcQuantitySet over generic property sets,
        then falls back to geometric calculation.
        
        Args:
            element: IFC element to extract quantities from
            storey: Building storey name (optional, will be extracted if not provided)
            
        Returns:
            Dictionary containing extracted quantities and metadata
        """
        quantities = {
            'element_id': element.id(),
            'global_id': getattr(element, 'GlobalId', None),
            'type': element.is_a(),
            'name': getattr(element, 'Name', None),
            'tag': getattr(element, 'Tag', None),
            'volume': None,
            'area': None,
            'length': None,
            'count': 1,
            'material': None,
            'storey': storey,
            'category': self._get_category(element),
        }
        
        # Step 1: Try to extract from IfcElementQuantity/IfcQuantitySet (BIM standard)
        qto_quantities = self._extract_ifc_element_quantities(element)
        if qto_quantities:
            quantities.update(qto_quantities)
        
        # Step 2: If not available, try generic Qto property sets (Revit exports)
        if not qto_quantities or all(quantities.get(qty) is None for qty in ['volume', 'area', 'length']):
            qto_properties = self._extract_qto_properties(element)
            if qto_properties:
                # Only update if values are still None
                for key, value in qto_properties.items():
                    if quantities.get(key) is None and value is not None:
                        quantities[key] = value
        
        # Step 3: Calculate geometric quantities as fallback
        if all(quantities.get(qty) is None for qty in ['volume', 'area', 'length']):
            geometric_quantities = self._calculate_geometric_quantities(element)
            if geometric_quantities:
                for key, value in geometric_quantities.items():
                    if quantities.get(key) is None and value is not None:
                        quantities[key] = value
        
        # Apply unit conversion (IFC units to meters)
        if quantities['volume'] is not None:
            # Volume: convert cubic units (scale^3)
            quantities['volume'] = quantities['volume'] * (self.unit_scale_factor ** 3)
        if quantities['area'] is not None:
            # Area: convert square units (scale^2)
            quantities['area'] = quantities['area'] * (self.unit_scale_factor ** 2)
        if quantities['length'] is not None:
            # Length: convert linear units (scale^1)
            quantities['length'] = quantities['length'] * self.unit_scale_factor
        
        # Extract material information
        quantities['material'] = self._extract_material(element)
        
        return quantities
    
    def _extract_ifc_element_quantities(self, element: Any) -> Dict[str, Optional[float]]:
        """
        Extract quantities from IfcElementQuantity or IfcQuantitySet.
        
        This is the BIM standard way of storing quantity take-off data.
        IfcElementQuantity contains IfcPhysicalQuantity objects like
        IfcQuantityVolume, IfcQuantityArea, IfcQuantityLength.
        
        Args:
            element: IFC element
            
        Returns:
            Dictionary of extracted quantities
        """
        quantities = {}
        
        try:
            # Get quantity sets using ifcopenshell utilities
            import ifcopenshell.util.element
            
            # Method 1: Get quantities directly from element
            qto_sets = ifcopenshell.util.element.get_qtos(element)
            
            if qto_sets:
                # Process each quantity set
                for qto_set_name, quantities_dict in qto_sets.items():
                    # Map standard IFC quantity names to our internal keys
                    quantity_mappings = {
                        'NetVolume': 'volume',
                        'GrossVolume': 'volume',
                        'Volume': 'volume',
                        'NetArea': 'area',
                        'GrossArea': 'area',
                        'Area': 'area',
                        'NetSideArea': 'area',
                        'TotalSurfaceArea': 'area',
                        'Length': 'length',
                        'NetLength': 'length',
                        'GrossLength': 'length',
                        'Perimeter': 'length',
                        'Width': 'length',
                        'Height': 'length',
                        'Depth': 'length',
                    }
                    
                    for qty_name, qty_value in quantities_dict.items():
                        if qty_name in quantity_mappings:
                            quantity_type = quantity_mappings[qty_name]
                            try:
                                value = float(qty_value)
                                # Use the first valid value found
                                if quantities.get(quantity_type) is None:
                                    quantities[quantity_type] = value
                            except (ValueError, TypeError):
                                continue
            
            # Method 2: Direct access to IfcElementQuantity via IsDefinedBy
            if not quantities and hasattr(element, 'IsDefinedBy'):
                for rel in element.IsDefinedBy:
                    if rel.is_a('IfcRelDefinesByProperties'):
                        if hasattr(rel, 'RelatingPropertyDefinition'):
                            prop_def = rel.RelatingPropertyDefinition
                            
                            # Check if it's an IfcElementQuantity
                            if prop_def.is_a('IfcElementQuantity'):
                                if hasattr(prop_def, 'Quantities'):
                                    for qty in prop_def.Quantities:
                                        qty_value = None
                                        qty_type_key = None
                                        
                                        # IfcQuantityVolume
                                        if qty.is_a('IfcQuantityVolume'):
                                            if hasattr(qty, 'VolumeValue'):
                                                qty_value = qty.VolumeValue
                                                qty_type_key = 'volume'
                                        
                                        # IfcQuantityArea
                                        elif qty.is_a('IfcQuantityArea'):
                                            if hasattr(qty, 'AreaValue'):
                                                qty_value = qty.AreaValue
                                                qty_type_key = 'area'
                                        
                                        # IfcQuantityLength
                                        elif qty.is_a('IfcQuantityLength'):
                                            if hasattr(qty, 'LengthValue'):
                                                qty_value = qty.LengthValue
                                                qty_type_key = 'length'
                                        
                                        # Store the quantity
                                        if qty_value is not None and qty_type_key:
                                            try:
                                                value = float(qty_value)
                                                if quantities.get(qty_type_key) is None:
                                                    quantities[qty_type_key] = value
                                            except (ValueError, TypeError):
                                                continue
                                
        except Exception as e:
            logger.debug(f"Error extracting IfcElementQuantity for element {element.id()}: {e}")
        
        return quantities
    
    def _extract_qto_properties(self, element: Any) -> Dict[str, Any]:
        """
        Extract quantities from IFC Qto (Quantity Take-Off) properties.
        
        Revit exports quantities in Qto sets. This method extracts
        common quantity properties like NetVolume, NetArea, etc.
        
        Args:
            element: IFC element
            
        Returns:
            Dictionary of extracted quantity properties
        """
        quantities = {}
        
        try:
            # Get all property sets for the element
            psets = ifcopenshell.util.element.get_psets(element)
            
            # Look for Qto properties
            for pset_name, props in psets.items():
                if 'Qto' in pset_name or 'Quantities' in pset_name:
                    # Common quantity property names
                    quantity_mappings = {
                        'NetVolume': 'volume',
                        'GrossVolume': 'volume',
                        'Volume': 'volume',
                        'NetArea': 'area',
                        'GrossArea': 'area',
                        'Area': 'area',
                        'NetSideArea': 'area',
                        'TotalSurfaceArea': 'area',
                        'Length': 'length',
                        'NetLength': 'length',
                        'GrossLength': 'length',
                        'Perimeter': 'length',
                        'Width': 'length',
                        'Height': 'length',
                        'Depth': 'length',
                    }
                    
                    for prop_name, prop_value in props.items():
                        if prop_name in quantity_mappings:
                            quantity_type = quantity_mappings[prop_name]
                            # Convert to float if possible
                            try:
                                value = float(prop_value)
                                # Use the first valid value found, or sum if multiple
                                if quantities.get(quantity_type) is None:
                                    quantities[quantity_type] = value
                            except (ValueError, TypeError):
                                continue
        except Exception as e:
            logger.debug(f"Error extracting Qto properties for element {element.id()}: {e}")
        
        return quantities
    
    def _calculate_geometric_quantities(self, element: Any) -> Dict[str, Optional[float]]:
        """
        Calculate quantities from element geometry (fallback method).
        
        This is used when IfcElementQuantity/IfcQuantitySet are not available.
        Calculates volume and area from geometric representation.
        Note: Units are already in IFC file units, will be converted later.
        
        Args:
            element: IFC element
            
        Returns:
            Dictionary with calculated volume, area, and length (in IFC units)
        """
        quantities = {
            'volume': None,
            'area': None,
            'length': None,
        }
        
        try:
            # Create shape geometry
            shape = ifcopenshell.geom.create_shape(self.settings, element)
            
            if shape:
                geometry = shape.geometry
                
                # Calculate volume from solid geometry
                try:
                    volume = geometry.volume()
                    if volume and volume > 0:
                        quantities['volume'] = volume
                except:
                    pass
                
                # Calculate surface area
                try:
                    # For area, calculate from faces
                    area = geometry.area()
                    if area and area > 0:
                        quantities['area'] = area
                except:
                    pass
                
                # Length calculation (for linear elements like beams)
                # This requires checking the element type and geometry
                element_type = element.is_a()
                if element_type in ['IfcBeam', 'IfcColumn']:
                    try:
                        # For linear elements, try to extract length from geometry
                        # This is approximate and may need refinement
                        bbox = geometry.bbox()
                        if bbox:
                            # Calculate approximate length from bounding box
                            # For beams/columns, longest dimension is typically length
                            dims = [bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2]]
                            length = max(dims)
                            if length > 0:
                                quantities['length'] = length
                    except:
                        pass
                
        except Exception as e:
            logger.debug(f"Could not calculate geometric quantities for element {element.id()}: {e}")
        
        return quantities
    
    def _get_category(self, element: Any) -> str:
        """
        Get the category/type name for the element.
        
        Args:
            element: IFC element
            
        Returns:
            Category name
        """
        # Try to get predefined type
        if hasattr(element, 'PredefinedType'):
            predefined_type = element.PredefinedType
            if predefined_type:
                return f"{element.is_a()}_{predefined_type}"
        
        # Fall back to element type
        return element.is_a()
    
    def _extract_material(self, element: Any) -> Optional[str]:
        """
        Extract material information from element.
        
        Args:
            element: IFC element
            
        Returns:
            Material name or None
        """
        try:
            # Get material from material association
            materials = ifcopenshell.util.element.get_materials(element)
            if materials:
                # Return the first material name found
                for material in materials:
                    if hasattr(material, 'Name'):
                        return material.Name
                    elif hasattr(material, 'MaterialSelect'):
                        mat_select = material.MaterialSelect
                        if hasattr(mat_select, 'Name'):
                            return mat_select.Name
        except Exception as e:
            logger.debug(f"Could not extract material for element {element.id()}: {e}")
        
        return None
    
    def extract_all_quantities(self, elements: List[Any], get_storey_fn=None) -> List[Dict[str, Any]]:
        """
        Extract quantities from a list of elements.
        
        Args:
            elements: List of IFC elements
            get_storey_fn: Optional function to get storey for an element (element -> str)
            
        Returns:
            List of quantity dictionaries
        """
        all_quantities = []
        
        for element in elements:
            try:
                # Get storey if function provided
                storey = None
                if get_storey_fn:
                    try:
                        storey = get_storey_fn(element)
                    except:
                        pass
                
                quantities = self.extract_quantities(element, storey=storey)
                all_quantities.append(quantities)
            except Exception as e:
                logger.warning(f"Failed to extract quantities for element {element.id()}: {e}")
                continue
        
        logger.info(f"Extracted quantities from {len(all_quantities)} elements")
        return all_quantities
