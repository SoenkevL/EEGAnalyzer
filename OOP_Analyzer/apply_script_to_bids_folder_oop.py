import argparse
import os
import sys
import uuid
from fileinput import filename

import yaml
import pandas as pd
from datetime import datetime
from EEG_processor import EEG_processor
from CSV_processor import CSVProcessor
import Alchemist
from multiprocesspandas import applyparallel


# This file is one of the two main files for computations.
# It is designed to be executed from the command line with two arguments:
# 1. A YAML configuration file specifying the experiments and their parameters.
# 2. A log file path where processing information will be stored.
# The script is used for processing files from a BIDS folder structure.


def check_file_exists_and_create_path(log_file: str, append_datetime: bool = False) -> (bool|str):
    """
    Ensures the path for a log file exists and optionally appends the current date and time to the filename.

    Args:
        log_file (str): Path of the log file, expected to end with `.log`.
        append_datetime (bool): If True, appends the current date and time to the log file name.

    Returns:
        str: The updated log file path if that was possible otherwise an emtpy string
    """
    # check if log_file could be a valid path, otherwise return False
    if not isinstance(log_file, (str ,os.PathLike)):
        return False

    # Create directory for log file if it doesn't exist
    if os.path.dirname(log_file) and not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Append timestamp to log file name if required
    if append_datetime:
        log_file = log_file.rstrip('.log')  # Remove `.log` extension for modification
        log_file = f'{log_file}__{datetime.today().strftime("%Y_%m_%d_%H_%M_%S")}.log'

    return log_file


def load_yaml_file(yaml_filepath: str) -> dict:
    """
    Loads a YAML configuration file into a dictionary.

    Args:
        yaml_filepath (str): The path to the YAML file.

    Returns:
        dict: A dictionary representation of the YAML configuration.
    """
    with open(yaml_filepath, 'r') as stream:
        data = yaml.safe_load(stream)
    return data

def add_or_update_dataset(session, config):
    """
    Add or update a dataset in the database.

    Args:
        config (dict): Configuration dictionary containing dataset information.

    Returns:
        datset_id: The id of the DataSet object that was added or updated.
    """
    dataset = Alchemist.add_or_update_dataset(
        session,
        dataset_name=config['name'],
        dataset_path=config['bids_folder'],
        dataset_description=config['description']
    )
    return dataset.id

def add_or_update_eeg(session, dataset_id, filepath):
    """
    Add or update an eeg in the database.

    Args:

    Returns:
        eeg_id: The id of the eeg object that was added or updated.
    """
    full_path = os.path.normpath(filepath)
    basename = os.path.basename(full_path)
    file_name, ext = os.path.splitext(basename)
    eeg = Alchemist.add_or_update_eeg_entry(
            session,
            dataset_id=dataset_id,
            filepath=full_path,
            filename=file_name,
            file_extension=ext,
        )
    return eeg

def add_or_update_experiment(session, experiment, run):
    experiment = Alchemist.add_or_update_experiment(
            session,
            metric_set_name=experiment['name'],
            run_name=run['name'],
            fs=run['sfreq'],
            start=experiment['epoching']['start_time'],
            stop=experiment['epoching']['stop_time'],
            window_len=experiment['epoching']['duration'],
            window_overlap=experiment['epoching']['overlap'],
            lower_cutoff=run['filter']['l_freq'],
            upper_cutoff=run['filter']['h_freq'],
            montage=run['montage']
    )
    return experiment

def populate_data_tables(session, experiment, table_exists='append'):
    experiment_id = experiment.id
    table_name = None
    for eeg in experiment.eegs:
        eeg_id = eeg.id
        result_path = Alchemist.get_result_path_from_ids(session, experiment_id=experiment_id, eeg_id=eeg_id)
        if result_path:
            data = pd.read_csv(result_path)
            table_name = Alchemist.add_metric_data_table(session, experiment_id, eeg_id, data, table_exists)
    session.commit()
    return table_name


def get_files_dataframe(bids_folder: str, infile_ending: str, outfile_ending: str, folder_extensions: str,
                        session, experiment, dataset_id) -> pd.DataFrame:
    """
    Creates a DataFrame containing valid file paths, their corresponding output paths,
    and the processed status (whether the output file already exists).

    Args:
        bids_folder (str): Path to the BIDS folder containing the files to process.
        outfile_ending (str): The expected output file ending.
        folder_extensions (str): The folder extension to be appended to the output folder name.
        infile_ending (str): The expected input file ending.

    Returns:
        pd.DataFrame: A DataFrame where:
            - The first column ('file_path') contains absolute file paths of valid files.
            - The second column ('outpath') contains the absolute path of the metrics output.
            - The third column ('already_processed') is a boolean indicating whether the output file exists.
    """
    valid_files = []

    # Walk through the BIDS folder structure
    for base, dirs, files in os.walk(bids_folder):
        for file in files:
            if not infile_ending or file.endswith(infile_ending):
                full_path = os.path.join(base, file)

                # Construct the output path based on file naming conventions
                outfile = file.replace(infile_ending, outfile_ending)
                splitbase = base.split('/')
                outpath = os.path.join(
                    *splitbase[:-1],
                    f'metrics{folder_extensions}',
                    outfile,
                )
                # Check if the output file exists
                already_processed = os.path.exists(outpath)

                # Add eeg to experiment in database
                eeg = add_or_update_eeg(session, dataset_id, full_path)
                if not eeg in experiment.eegs:
                    experiment.eegs.append(eeg)
                Alchemist.add_result_path(session, experiment.id, eeg.id, outpath)
                # Append file data to list
                valid_files.append({'file_path': full_path, 'outpath': outpath, 'already_processed': already_processed})
                 # Add file to database

    # Create the DataFrame from the collected information
    df = pd.DataFrame(valid_files, columns=['file_path', 'outpath', 'already_processed'])

    return df


def process_file(row, metric_set_name, annotations, lfreq, hfreq, montage, ep_start, ep_stop, ep_dur, ep_overlap, sfreq,
                 recompute):
    """
    Processes a single file.

    Args:
        row (pd.Series): A row from the DataFrame containing file information.
        metric_set_name (str): The name of the metric set to compute.
        annotations (list): The annotations of interest.
        lfreq (int): Lower cutoff frequency for filtering.
        hfreq (int): Upper cutoff frequency for filtering.
        montage (str): The montage to apply.
        ep_start (int): Epoching start time.
        ep_stop (int): Epoching stop time.
        ep_dur (int): Epoch duration.
        ep_overlap (int): Overlap of epochs.
        sfreq (int): Sampling frequency.
        recompute (bool): Whether to recompute metrics.
    """
    file_path = row['file_path']
    outpath = row['outpath']
    already_processed = row['already_processed']

    if not already_processed or recompute:
        print(f"Processing file: {file_path}")
        print(f"Output path: {outpath}")

        # Initialize EEG_processor and compute metrics
        if file_path.endswith(".fif") or file_path.endswith(".edf"):
            eeg_processor = EEG_processor(file_path)
            result = eeg_processor.compute_metrics(
                metric_set_name,
                annotations,
                outpath,
                lfreq,
                hfreq,
                montage,
                ep_start,
                ep_stop,
                ep_dur,
                ep_overlap,
                sfreq,
                recompute,
            )
        elif file_path.endswith(".csv"):
            csv_processor = CSVProcessor(file_path, sfreq=sfreq)
            result = csv_processor.compute_metrics(
                metric_set_name,
                outpath,
                lfreq,
                hfreq,
                ep_start,
                ep_stop,
                ep_dur,
                ep_overlap,
                sfreq,
                recompute,
            )
        else:
            result = 'Result not computed. Output file ending not recognized.'
        print(f"Result: {result}")
    else:
        print(f"Skipping already processed file: {file_path}")


def process_experiment(config: dict, log_file: str, num_processes: int=4):
    """
    Processes experiments and their respective runs as specified in the YAML configuration.

    Args:
        config (dict): The dictionary representation of the YAML configuration file.
        log_file (str): The path to the log file where outputs and logs will be saved.
    """
    # Redirect all print outputs to the log file
    if log_file:
        log_stream = open(log_file, 'w')
        sys.stdout = log_stream  # Redirect print statements to log file
    print(f'{"*" * 102}\n{"*" * 40} {datetime.today().strftime("%Y-%m-%d %H:%M:%S")} {"*" * 40}\n{"*" * 102}\n')
        # Iterate through experiments defined in the configuration
    for experiment in config['experiments']:
        # make sure we can access our sqlite base
        engine = Alchemist.initialize_tables(experiment['sqlite_path'])
        with Alchemist.Session(engine) as session:
            # Extract experiment-level configuration
            exp_name = experiment['name']
            input_file_ending = experiment['input_file_ending']
            bids_folder = experiment['bids_folder']
            annotations = experiment['annotations_of_interest']
            outfile_ending = experiment['outfile_ending']
            recompute = experiment['recompute']
            epoching = experiment['epoching']
            ep_start, ep_dur, ep_stop, ep_overlap = (
                epoching['start_time'],
                epoching['duration'],
                epoching['stop_time'],
                epoching['overlap'],
            )
            metric_set_name = experiment['metric_set_name']

            # add or update dataset in sqlite database
            dataset_id = add_or_update_dataset(session, experiment)
            print(f"Using dataset ID: {dataset_id}")

            # Iterate through runs for each experiment
            for run in experiment['runs']:
                # Extract run-level configuration
                run_name = run['name']
                lfreq = run['filter']['l_freq']
                hfreq = run['filter']['h_freq']
                sfreq = run['sfreq']
                montage = run['montage']
                folder_extensions = run['metrics_prefix']

                print(
                    f'{"#" * 20} Running experiment "{exp_name}" and run "{run_name}" on folder "{bids_folder}" {"#" * 20}\n')

                experiment_object = add_or_update_experiment(session, experiment, run)
                # create first experiment, then files df and add experiment to each eeg
                # Create DataFrame of valid files to process (also adds the eegs to the database)
                files_df = get_files_dataframe(bids_folder, input_file_ending, outfile_ending, folder_extensions,
                                               session, experiment_object, dataset_id)
                print(f"Generated DataFrame with {len(files_df)} files:")
                # print(files_df.head())


                n_chunks = max(len(files_df) // num_processes, 1)
                num_processes = min(n_chunks, num_processes)
                files_df.apply_parallel(
                    process_file,
                    metric_set_name=metric_set_name,
                    annotations=annotations,
                    lfreq=lfreq,
                    hfreq=hfreq,
                    montage=montage,
                    ep_start=ep_start,
                    ep_stop=ep_stop,
                    ep_dur=ep_dur,
                    ep_overlap=ep_overlap,
                    sfreq=sfreq,
                    recompute=recompute,
                    axis=0,
                    num_processes=num_processes,
                    n_chunks=n_chunks,
                )

                # TODO: add the computed result frames to the database by iterating over the eegs of the experiment
                populate_data_tables(session, experiment_object)

    # Print a final message indicating completion
    print(f"\n{'*' * 50}")
    print(f"All processing complete. Results stored in database: {experiment['sqlite_path']}")
    print(f"{'*' * 50}\n")

    if log_file:
        log_stream.close()

if __name__ == "__main__":
    # Main entry point of the program
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
