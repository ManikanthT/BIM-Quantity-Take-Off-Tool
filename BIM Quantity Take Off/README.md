# BIM Quantity Take-Off (QTO) Tool

A production-quality Python tool for extracting quantities from IFC (Industry Foundation Classes) models and generating professional Bill of Quantities (BOQ) for civil engineering applications.

## Features

- **IFC File Handling**: Supports IFC2x3 and IFC4 models with automatic unit conversion (mm → m)
- **Civil Engineering Elements**: Extracts quantities for IfcBeam, IfcColumn, IfcSlab, IfcWall, IfcFooting
- **Quantity Extraction**: Uses IfcElementQuantity/IfcQuantitySet (BIM standard) with geometric fallback
- **BOQ Generation**: Groups by element type, building storey, or material
- **Professional Excel Export**: One sheet per element category with clean formatting
- **Production-Ready**: Comprehensive error handling, logging, and modular architecture

## Technology Stack

- **Python 3.8+**: Core programming language
- **IFCOpenShell**: IFC file parsing and geometry processing
- **Pandas**: Data manipulation and DataFrame operations
- **OpenPyXL**: Excel (.xlsx) file generation and formatting

## Installation

1. Clone or download this repository

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

**Note**: `ifcopenshell` requires additional system dependencies. On Windows, it should install automatically. On Linux/Mac, you may need OpenCASCADE libraries:
```bash
sudo apt-get install libopencascade-dev  # Ubuntu/Debian
```

## Usage

### Basic Usage

```bash
python main.py input.ifc output.xlsx
```

### Command-Line Options

```bash
python main.py <ifc_file> <output_file> [options]

Options:
  --grouping {type,storey,material,all}
                        Grouping level for BOQ items (default: type)
                        - type: Group by element type (IfcWall, IfcSlab, etc.)
                        - storey: Group by building storey
                        - material: Group by material
                        - all: Group by element type, storey, and material
  --rates RATES         Path to rates JSON file (default: rates.json)
  --cost                Enable basic cost estimation
  --verbose, -v         Enable verbose logging
  -h, --help           Show help message
```

### Examples

```bash
# Basic extraction (groups by element type)
python main.py building_model.ifc boq_output.xlsx

# Group by building storey
python main.py building_model.ifc boq_output.xlsx --grouping storey

# Group by material
python main.py building_model.ifc boq_output.xlsx --grouping material

# Detailed grouping (type + storey + material)
python main.py building_model.ifc boq_output.xlsx --grouping all

# Verbose output for debugging
python main.py building_model.ifc boq_output.xlsx --verbose

# Generate Priced BOQ (Cost Estimation)
python main.py building_model.ifc boq_priced.xlsx --cost

# Use custom rates file
python main.py building_model.ifc boq_priced.xlsx --cost --rates my_rates.json
```

### Programmatic Usage

```python
from src.ifc_reader import IFCReader
from src.quantity_extractor import QuantityExtractor
from src.boq_generator import BOQGenerator
from src.excel_exporter import ExcelExporter

# Read IFC file
reader = IFCReader('model.ifc')
ifc_file = reader.get_file()
project_info = reader.get_project_info()

# Extract civil engineering elements
elements = reader.get_civil_engineering_elements()

# Extract quantities
unit_scale_factor = project_info.get('unit_scale_factor', 0.001)
extractor = QuantityExtractor(ifc_file, unit_scale_factor=unit_scale_factor)
quantities = extractor.extract_all_quantities(
    elements,
    get_storey_fn=reader.get_element_storey
)

# Generate BOQ
boq_gen = BOQGenerator()
boq_gen.load_quantities(quantities)
boq_df = boq_gen.generate_boq(grouping_level='type')
summary = boq_gen.get_summary(boq_df)

# Export to Excel
exporter = ExcelExporter('output.xlsx')
exporter.export_boq(boq_df, summary=summary, project_info=project_info)
```

## Output Format

The tool generates an Excel workbook with:

### BOQ Sheets (One per Element Type)
Each element type (Wall, Slab, Column, Beam, Footing) gets its own sheet with columns:

| Item No | Element Type | Description | Unit | Quantity | Storey | Material |
|---------|--------------|-------------|------|----------|--------|----------|
| 1 | IfcWall | Wall - Concrete | m³ | 125.500 | Ground Floor | Concrete |
| 2 | IfcWall | Wall - Brick | m² | 450.250 | First Floor | Brick |

**Additional columns:** volume_m3, area_m2, length_m, count (for reference)

### Summary Sheet
Aggregated statistics:
- Total items
- Total volumes (m³)
- Total areas (m²)
- Total lengths (m)
- Total counts
- List of element types found

### Project Information Sheet
IFC file metadata:
- Project name
- Building name
- IFC schema version
- Unit scale factor
- File path

## Supported Element Types

The tool extracts quantities from these civil engineering elements:
- **IfcBeam**: Structural beams
- **IfcColumn**: Structural columns
- **IfcSlab**: Floor/roof slabs
- **IfcWall**: Structural and non-structural walls
- **IfcFooting**: Foundation footings

**Non-physical elements are automatically filtered out:**
- IfcOpeningElement (openings)
- IfcAnnotation (annotations)
- IfcGrid (grid lines)
- IfcSpace (spaces)

## Quantity Extraction

The tool uses a three-tier extraction strategy:

1. **Priority 1: IfcElementQuantity/IfcQuantitySet** (BIM Standard)
   - Extracts from `IfcQuantityVolume`, `IfcQuantityArea`, `IfcQuantityLength`
   - Most accurate, preferred method

2. **Priority 2: Qto Property Sets** (Revit Exports)
   - Extracts from property sets with "Qto" or "Quantities" in name
   - Maps common properties: NetVolume, GrossArea, Length, etc.

3. **Priority 3: Geometric Calculation** (Fallback)
   - Calculates from element geometry using ifcopenshell
   - Used when quantity properties are not available

**Unit Conversion:**
- Automatically detects IFC file units
- Converts to meters (m) for volumes, areas, and lengths
- Defaults to mm → m conversion (0.001 scale factor) if units cannot be detected

## BOQ Grouping Options

- **type** (default): Groups by element type (all walls together, all slabs together)
- **storey**: Groups by building storey (Ground Floor, First Floor, etc.)
- **material**: Groups by material (all Concrete together, all Brick together)
- **all**: Groups by combination of type, storey, and material (most detailed)

## Project Structure

```
BIM/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── ifc_reader.py            # IFC file reading, validation, unit detection
│   ├── quantity_extractor.py    # Quantity extraction (Qto + geometric)
│   ├── boq_generator.py         # BOQ generation and organization
│   ├── excel_exporter.py        # Excel export with formatting
│   └── main.py                  # CLI interface and orchestration
├── main.py                      # Entry point
├── config.py                    # Configuration management
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── IMPLEMENTATION_PLAN.md       # Detailed implementation documentation
└── IFC_ISSUES_NOTES.md         # Common IFC issues and solutions
```

## Configuration

Configuration can be customized through:

1. **Environment Variables**: Create a `.env` file:
```env
BIM_QTO_GROUPING=type
BIM_QTO_LOG_LEVEL=INFO
```

2. **Config Module**: Edit `config.py` for advanced settings

## Troubleshooting

### Common Issues

**"IFC file not found"**
- Verify the file path is correct
- Ensure the file has `.ifc` extension

**"Invalid IFC file"**
- Ensure the IFC file is not corrupted
- Try exporting from Revit again
- Verify the file is a valid IFC2x3 or IFC4 file

**"No building elements found"**
- Check that the IFC file contains the required element types (Beam, Column, Slab, Wall, Footing)
- Verify elements are not filtered as non-physical (openings, annotations)

**"Empty quantities in BOQ"**
- Some IFC files may not have quantity properties exported
- The tool will attempt geometric calculation as fallback
- Check if elements have valid geometry in the source model
- In Revit, enable "Include Quantity Take-Offs" in export settings

**"Missing dependencies"**
- Ensure all packages in `requirements.txt` are installed
- On Linux, install OpenCASCADE development libraries (see Installation)

For detailed information on handling IFC file issues, see [IFC_ISSUES_NOTES.md](IFC_ISSUES_NOTES.md).

## Best Practices for IFC Export

To ensure best results with this tool, when exporting IFC files from Revit:

1. **Enable Quantity Exports:**
   - Export Settings → Include Quantity Take-Offs
   - Ensures IfcElementQuantity is populated

2. **Assign Storeys:**
   - Ensure all elements are properly assigned to building storeys
   - Improves BOQ organization and grouping

3. **Material Assignment:**
   - Assign materials at instance or type level
   - Use consistent material naming conventions

4. **Unit Consistency:**
   - Export with consistent units (mm is recommended for Revit)
   - Check project unit settings before export

5. **Element Filtering:**
   - Export only required element types
   - Reduces file size and processing time

## Development

### Code Quality

The code follows Python best practices:
- Type hints where applicable
- Comprehensive docstrings
- Modular architecture with clear separation of concerns
- Error handling and logging throughout
- PEP 8 style guide compliance

### Testing

Test the tool with sample IFC files:
1. Export a test model from Revit
2. Run the tool: `python main.py test_model.ifc test_output.xlsx`
3. Verify quantities in the Excel output
4. Compare with manual calculations if needed

### Extending the Tool

To add support for additional element types:
1. Add element type to `get_civil_engineering_elements()` in `ifc_reader.py`
2. Update quantity extraction logic if needed
3. Test with sample IFC files containing the new element type

## Documentation

- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)**: Detailed implementation plan and architecture
- **[IFC_ISSUES_NOTES.md](IFC_ISSUES_NOTES.md)**: Common IFC issues and how the code handles them

## License

This tool is provided as-is for educational and professional use.

## Version History

- **v1.0.0**: Initial production release
  - IFC2x3 and IFC4 support
  - Unit conversion (mm → m)
  - Quantity extraction (IfcElementQuantity + geometric fallback)
  - BOQ generation with multiple grouping options
  - Excel export with separate sheets per element type
  - Storey and material extraction
  - Filtering of non-physical elements

## Acknowledgments

Built with:
- [ifcopenshell](https://github.com/IfcOpenShell/IfcOpenShell) - IFC file processing
- [pandas](https://pandas.pydata.org/) - Data manipulation
- [openpyxl](https://openpyxl.readthedocs.io/) - Excel file generation

---

**Note**: This tool is designed for production use in civil engineering and construction projects. Ensure proper validation of quantities before use in cost estimation or project documentation.

**For Portfolio/CV Use**: This project demonstrates:
- BIM software development skills
- IFC file processing expertise
- Python programming best practices
- Production-quality code architecture
- Civil engineering domain knowledge
