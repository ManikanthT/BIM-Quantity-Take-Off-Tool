"""
Cost Estimator CLI
"""
import sys
import argparse
import logging
from pathlib import Path

# Add the parent directory to the path so we can import src
sys.path.insert(0, str(Path(__file__).parent))

from src.cost_estimator import CostEstimator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('cost_estimate')

def main():
    parser = argparse.ArgumentParser(description='BIM Smart Cost Estimator')
    parser.add_argument('input_file', help='Input BOQ Excel file')
    parser.add_argument('output_file', help='Output Priced BOQ Excel file')
    parser.add_argument('--rates', default='rates.json', help='Path to rates JSON file')
    
    args = parser.parse_args()
    
    try:
        estimator = CostEstimator(args.rates)
        estimator.process_boq(args.input_file, args.output_file)
        print(f"Success! Priced BOQ generated at: {args.output_file}")
    except Exception as e:
        logger.error(f"Estimation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
