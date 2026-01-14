"""
IFC File Reader Module
Handles reading and parsing IFC files exported from Revit.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
import ifcopenshell
from ifcopenshell import file as ifc_file_module

logger = logging.getLogger(__name__)


class IFCReader:
    """
    Reads and parses IFC files for quantity extraction.
    
    This class provides a high-level interface for working with IFC files,
    with proper error handling and logging for production use.
    """
    
    def __init__(self, ifc_path: str):
        """
        Initialize the IFC reader.
        
        Args:
            ifc_path: Path to the IFC file
            
        Raises:
            FileNotFoundError: If the IFC file doesn't exist
            ValueError: If the file is not a valid IFC file
        """
        self.ifc_path = Path(ifc_path)
        if not self.ifc_path.exists():
            raise FileNotFoundError(f"IFC file not found: {ifc_path}")
        
        self.ifc_file: Optional[Any] = None
        self._load_file()
    
    def _load_file(self) -> None:
        """Load and validate the IFC file."""
        try:
            logger.info(f"Loading IFC file: {self.ifc_path}")
            self.ifc_file = ifcopenshell.open(str(self.ifc_path))
            logger.info(f"Successfully loaded IFC file. Schema: {self.ifc_file.schema}")
        except Exception as e:
            logger.error(f"Failed to load IFC file: {e}")
            raise ValueError(f"Invalid IFC file: {e}") from e
    
    def get_file(self) -> Any:
        """
        Get the underlying IFC file object.
        
        Returns:
            The ifcopenshell file object
        """
        if self.ifc_file is None:
            raise RuntimeError("IFC file not loaded")
        return self.ifc_file
    
    def get_elements_by_type(self, element_type: str) -> List[Any]:
        """
        Get all elements of a specific type from the IFC file.
        
        Args:
            element_type: IFC element type (e.g., 'IfcWall', 'IfcSlab', 'IfcColumn')
            
        Returns:
            List of IFC elements of the specified type
        """
        if self.ifc_file is None:
            raise RuntimeError("IFC file not loaded")
        
        try:
            elements = self.ifc_file.by_type(element_type)
            logger.debug(f"Found {len(elements)} elements of type {element_type}")
            return elements
        except Exception as e:
            logger.warning(f"Error retrieving elements of type {element_type}: {e}")
            return []
    
    def get_civil_engineering_elements(self) -> List[Any]:
        """
        Get specified civil engineering elements from the IFC file.
        
        Extracts only the required element types:
        - IfcBeam
        - IfcColumn
        - IfcSlab
        - IfcWall
        - IfcFooting
        
        Filters out non-physical elements (openings, annotations, grids).
        
        Returns:
            List of building elements for quantity take-off
        """
        # Required element types for civil engineering QTO
        element_types = [
            'IfcBeam',
            'IfcColumn',
            'IfcSlab',
            'IfcWall',
            'IfcFooting',
        ]
        
        all_elements = []
        for elem_type in element_types:
            elements = self.get_elements_by_type(elem_type)
            # Filter out non-physical elements
            filtered_elements = self._filter_physical_elements(elements)
            all_elements.extend(filtered_elements)
        
        logger.info(f"Total civil engineering elements found: {len(all_elements)}")
        return all_elements
    
    def _filter_physical_elements(self, elements: List[Any]) -> List[Any]:
        """
        Filter out non-physical elements (openings, annotations, grids).
        
        Args:
            elements: List of IFC elements
            
        Returns:
            Filtered list containing only physical elements
        """
        filtered = []
        excluded_types = [
            'IfcOpeningElement',
            'IfcSpace',
            'IfcAnnotation',
            'IfcGrid',
            'IfcOpeningStandardCase',
        ]
        
        for element in elements:
            # Skip if element type is excluded
            if element.is_a() in excluded_types:
                continue
            
            # Skip if element is a void (opening)
            if hasattr(element, 'HasOpenings') and element.HasOpenings:
                # Check if this is actually an opening element
                continue
            
            # Additional check: skip if Name or Tag indicates it's an opening/annotation
            name = getattr(element, 'Name', None)
            tag = getattr(element, 'Tag', None)
            
            if name and any(keyword in str(name).lower() for keyword in ['opening', 'void', 'annotation']):
                continue
            if tag and any(keyword in str(tag).lower() for keyword in ['opening', 'void', 'annotation']):
                continue
            
            filtered.append(element)
        
        return filtered
    
    def get_all_building_elements(self) -> List[Any]:
        """
        Get all building elements from the IFC file (legacy method).
        Uses get_civil_engineering_elements() for consistency.
        
        Returns:
            List of all building elements
        """
        return self.get_civil_engineering_elements()
    
    def get_unit_scale_factor(self) -> float:
        """
        Get the unit scale factor to convert IFC units to meters.
        
        IFC files typically use mm as base unit, but this checks the actual
        unit specification in the file.
        
        Returns:
            Scale factor to convert to meters (default: 0.001 for mm to m)
        """
        if self.ifc_file is None:
            raise RuntimeError("IFC file not loaded")
        
        try:
            # Get project units
            projects = self.ifc_file.by_type('IfcProject')
            if not projects:
                logger.warning("No project found, assuming mm units")
                return 0.001  # Default: mm to m
            
            project = projects[0]
            
            # Check UnitsInContext
            if hasattr(project, 'UnitsInContext'):
                units_context = project.UnitsInContext
                if units_context and hasattr(units_context, 'Units'):
                    units = units_context.Units
                    
                    # Check length unit
                    for unit in units:
                        if unit.is_a('IfcNamedUnit'):
                            if hasattr(unit, 'UnitType') and unit.UnitType == 'LENGTHUNIT':
                                # Check if it's SI unit
                                if hasattr(unit, 'Dimensions') or hasattr(unit, 'Name'):
                                    # Check for meter
                                    if hasattr(unit, 'Name') and unit.Name:
                                        name = str(unit.Name).upper()
                                        if 'METER' in name or 'METRE' in name:
                                            if 'MILLI' in name:
                                                return 0.001  # mm to m
                                            elif 'CENTI' in name:
                                                return 0.01  # cm to m
                                            else:
                                                return 1.0  # m
                    # Check IfcSIUnit
                    for unit in units:
                        if unit.is_a('IfcSIUnit'):
                            if hasattr(unit, 'UnitType') and unit.UnitType == 'LENGTHUNIT':
                                if hasattr(unit, 'Prefix'):
                                    prefix = str(getattr(unit, 'Prefix', '')).upper()
                                    if prefix == 'MILLI':
                                        return 0.001  # mm to m
                                    elif prefix == 'CENTI':
                                        return 0.01  # cm to m
                                    else:
                                        return 1.0  # m
        except Exception as e:
            logger.warning(f"Could not determine units from IFC file: {e}. Assuming mm units.")
        
        # Default: assume mm (most common in Revit exports)
        return 0.001
    
    def get_project_info(self) -> Dict[str, Any]:
        """
        Extract project information from the IFC file.
        
        Returns:
            Dictionary containing project metadata
        """
        if self.ifc_file is None:
            raise RuntimeError("IFC file not loaded")
        
        project_info = {
            'schema': self.ifc_file.schema,
            'file_path': str(self.ifc_path),
            'unit_scale_factor': self.get_unit_scale_factor(),
            'base_unit': 'm' if self.get_unit_scale_factor() == 1.0 else 'mm',
        }
        
        try:
            # Get the project
            projects = self.ifc_file.by_type('IfcProject')
            if projects:
                project = projects[0]
                project_info['project_name'] = getattr(project, 'Name', None)
                project_info['project_id'] = getattr(project, 'GlobalId', None)
            
            # Get building information if available
            buildings = self.ifc_file.by_type('IfcBuilding')
            if buildings:
                building = buildings[0]
                project_info['building_name'] = getattr(building, 'Name', None)
                project_info['building_id'] = getattr(building, 'GlobalId', None)
        except Exception as e:
            logger.warning(f"Could not extract all project info: {e}")
        
        return project_info
    
    def get_element_storey(self, element: Any) -> Optional[str]:
        """
        Get the building storey for an element.
        
        Args:
            element: IFC element
            
        Returns:
            Storey name or None if not assigned
        """
        try:
            # Check if element has ContainedInStructure
            if hasattr(element, 'ContainedInStructure'):
                contained_in = element.ContainedInStructure
                if contained_in:
                    for relation in contained_in:
                        if hasattr(relation, 'RelatingStructure'):
                            structure = relation.RelatingStructure
                            # Check if it's a storey
                            if structure.is_a('IfcBuildingStorey'):
                                return getattr(structure, 'Name', None) or getattr(structure, 'LongName', None)
            
            # Alternative: Check using ifcopenshell utilities
            try:
                import ifcopenshell.util.placement
                storey = ifcopenshell.util.element.get_container(element, 'IfcBuildingStorey')
                if storey:
                    return getattr(storey, 'Name', None) or getattr(storey, 'LongName', None)
            except:
                pass
        except Exception as e:
            logger.debug(f"Could not extract storey for element {element.id()}: {e}")
        
        return None
