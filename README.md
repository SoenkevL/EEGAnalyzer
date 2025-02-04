# EEGAnalyzer

A comprehensive tool for analyzing EEG data with focus on chaotic dynamics, complexity assessment, fractal properties, and entropy calculations.

## Features

- **Analysis Capabilities**:
  - Chaotic dynamics analysis
  - Complexity metrics evaluation
  - Fractal property detection
  - Entropy calculation methods

- **Modular Architecture**:
  - Preset metric sets to start analysis right away 
  - Extensible design for easily adding custom functions as metrics
  - Supports 1D and 2D timeseries data
  - Primarily written for EEG analysis while also providing functionality for csv data

- **Configuration**:
  - Adjustable parameters for analysis focused on timeseries.
  - Full folder (and subfolder) structures can be processed at once.
  - Ability to include only certain files based on name
  - Full control over the output directories of the computed metrics
  - Parameters for epoching like start, stop, duration and window overlap
  - Filtering
  - Integration with annotations of edf files to include only annotated data segments and exclude bad channels
  - Choosing predefined sets of metrics (python functions) to be applied to the data

- **Logging System**:
  - Tracks processing information for better debugging and monitoring

- **Output Format**:
  - Metrics saved in standardized CSV format

## Requirements
- Python 3.8+

## Installation with example

### 1. Clone the repository:

```
git clone https://github.com/SoenkevL/EEGAnalyzer.git 
cd EEGAnalyzer
```

### 2. Create and activate virtual environment

```
python3 -m venv .eeg_venv
source .eeg_venv/bin/activate  # On Windows use `.eeg_venv\Scripts\activate`
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Prepare example data directory structure

```
mkdir -p examples/eeg
```

### 5. Move downloaded file to correct location

Now we need to download an example eeg to test the pipeline on. For this we use an open source edf file from kaggle
https://www.kaggle.com/datasets/abhishekinnvonix/seina-scalp-epilepsy-dataset?resource=download (14.10.2024)  
One can use all 5 files or just one of them, but we focus only on using one in this example, after downloading the file
move it to the right folder with the following command

```
mv PN00-1.edf examples/eeg/PN001-original.edf
```

This will also rename the file so that it is properly handled by the config (touched upon in step 7)

### 6. Launch Jupyter notebook for preprocessing

Now we can run the notebook in the *eeg_reading_and_preprocessing* folder to do an inspection of the example eeg

### 7. Inspecting the configuration file

In order to process the files we use configuration files. An example of such a file can be found in
*example/example_config_eeg.yaml* \
Within the configuration file alot of parameters can be set which are important for the processing steps. This includes
things like: Data folder, metric set, epoching, annotation usage and more. All parameters are described within the
example config file.

### 8. Run the main script with configuration

In order to calculate the metrics on our eeg files we can run the example configuration using the following command.
Make sure the virtual environment is activated and the requirements are installed.

```
python3 OOP_Analyzer/apply_script_to_bids_folder_oop.py \
    --yaml_config example/example_config_eeg.yaml \
    --logfile_path example/test.log
```

