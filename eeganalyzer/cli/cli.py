"""
Command-line interface for EEG analysis.

This module provides the main entry point for the EEG analysis command-line interface.
"""

import argparse
import os
import sys
from datetime import datetime

from eeganalyzer.core.processor import process_experiment
from eeganalyzer.utils.config import load_yaml_file, check_file_exists_and_create_path


def main():
    """
    Main entry point for the EEG analysis command-line interface.
    
    This function parses command-line arguments and runs the EEG analysis pipeline.
    """
    # Parse input arguments from the command line
    parser = argparse.ArgumentParser(
        description='Processes files from a BIDS folder structure based on a YAML configuration file.'
    )
    parser.add_argument('--yaml_config', type=str, required=True, help='Path to the YAML configuration file.')
    parser.add_argument('--logfile_path', type=str, required=False, default=False, help='Path to the log file (must end with .log).')

    args = parser.parse_args()
    yaml_file = args.yaml_config
    log_file = args.logfile_path

    # Ensure the log file path exists and append a timestamp
    log_file = check_file_exists_and_create_path(log_file, append_datetime=True)

    # Load configuration from the YAML file
    config = load_yaml_file(yaml_file)

    # Process the experiments as defined in the configuration
    process_experiment(config, log_file)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())