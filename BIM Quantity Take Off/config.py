"""
Configuration Module
Centralized configuration management for the BIM QTO tool.
"""

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration settings for the BIM QTO tool."""
    
    # Default grouping level
    DEFAULT_GROUPING_LEVEL = os.getenv('BIM_QTO_GROUPING', 'category')
    
    # Logging configuration
    LOG_LEVEL = os.getenv('BIM_QTO_LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Excel export settings
    EXCEL_DATE_FORMAT = '%Y-%m-%d'
    EXCEL_HEADER_COLOR = '366092'  # Blue
    EXCEL_SUMMARY_COLOR = '70AD47'  # Green
    EXCEL_INFO_COLOR = '4472C4'  # Blue
    
    # IFC processing settings
    IFC_GEOMETRY_SETTINGS = {
        'USE_WORLD_COORDS': True,
        'USE_BREP_DATA': True,
        'SEW_SHELLS': True,
    }
    
    # Quantity extraction settings
    QUANTITY_PRECISION = 3  # Decimal places for quantities
    MIN_QUANTITY_VALUE = 0.001  # Minimum value to consider (filter out noise)
    
    # BOQ settings
    BOQ_ITEM_NUMBERING_START = 1
    BOQ_DESCRIPTION_TEMPLATE = "{element_type} - {material}"
    
    # Supported element types for quantity extraction
    SUPPORTED_ELEMENT_TYPES = [
        'IfcWall',
        'IfcSlab',
        'IfcColumn',
        'IfcBeam',
        'IfcFooting',
        'IfcPile',
        'IfcRailing',
        'IfcStair',
        'IfcRoof',
        'IfcCurtainWall',
        'IfcBuildingElementProxy',
        'IfcDoor',
        'IfcWindow',
    ]
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration as a dictionary."""
        return {
            'default_grouping_level': cls.DEFAULT_GROUPING_LEVEL,
            'log_level': cls.LOG_LEVEL,
            'quantity_precision': cls.QUANTITY_PRECISION,
            'supported_element_types': cls.SUPPORTED_ELEMENT_TYPES,
        }
