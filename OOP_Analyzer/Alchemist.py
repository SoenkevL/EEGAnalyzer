import uuid
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from sqlalchemy import ForeignKey, String, create_engine, text, select, DateTime, func, Integer, Table, Column
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Union
# declaring a shorthand for the declarative base class
class Base(DeclarativeBase):
    pass

# defining the classes for our project with the correct meta data
class DataSet(Base):
    __tablename__ = "dataset"

    id: Mapped[str] = mapped_column(primary_key=True, default=str(uuid.uuid4().hex))
    last_altered: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str]
    description: Mapped[Optional[str]]

    eegs: Mapped[List["EEG"]] = relationship(back_populates="dataset")

class EEG(Base):
    __tablename__ = "eeg"

    id = mapped_column(String, primary_key=True, default=str(uuid.uuid4().hex))
    dataset_id = mapped_column(ForeignKey("dataset.id"))
    last_altered = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    filename = mapped_column(String, nullable=False)
    filetype = mapped_column(String, nullable=False)
    filepath = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]]

    dataset: Mapped[DataSet] = relationship(back_populates='eegs')
    # experiments: Mapped[List['Experiment']] = relationship(back_populates='eegs', secondary="association_table")
    experiments: Mapped[List['Experiment']] = relationship(back_populates='eegs', secondary="result_association")

class Experiment(Base):
    __tablename__ = "experiment"

    id = mapped_column(String, primary_key=True, default=str(uuid.uuid4().hex))
    last_altered: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    metric_set_name = mapped_column(String, nullable=False)  # Name of the metric set (e.g., 'entropy')
    run_name = mapped_column(String, nullable=False)  # Name of the metric set (e.g., 'entropy')
    description: Mapped[Optional[str]]

    fs: Mapped[Optional[int]]
    start: Mapped[Optional[int]]
    stop: Mapped[Optional[int]]
    window_len: Mapped[Optional[int]]
    window_overlap: Mapped[Optional[int]]
    lower_cutoff: Mapped[Optional[float]]
    upper_cutoff: Mapped[Optional[float]]
    montage: Mapped[Optional[str]]

    # eegs: Mapped[List['EEG']] = relationship(back_populates='experiments', secondary="association_table")
    eegs: Mapped[List['EEG']] = relationship(back_populates='experiments', secondary="result_association")
    # Metric data will be stored in dynamically created tables


class ResultAssociation(Base):
    __tablename__ = "result_association"
    experiment_id = mapped_column(ForeignKey("experiment.id"), primary_key=True)
    eeg_id = mapped_column(ForeignKey("eeg.id"), primary_key=True)
    result_path: Mapped[Optional[str]]


# functions to modify tables in the database
def remove_table(engine, table_name: str, del_from_metadata = True):
    try:
        # Execute the DROP TABLE command
        stmt = text(f'DROP TABLE IF EXISTS {table_name}')
        with engine.connect() as connection:
            connection.execute(stmt)
            print(f"Table {table_name} removed successfully.")

        # Remove the table from the MetaData object
        table = Base.metadata.tables.get(table_name)
        if table is not None and del_from_metadata:
            Base.metadata.remove(table)
            print(f"Table {table_name} removed from metadata successfully.")
    except SQLAlchemyError as e:
        print(f"Error: {e}")

def add_column(engine, table_name:str , column_name:str, column_type:str):
    try:
        # Compile the column type for the specific database dialect

        # Execute the ALTER TABLE command
        stmt = text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}')
        with Session(engine) as session:
            result = session.execute(stmt)
            print(f"Column {column_name} added successfully.")
            session.commit()
    except SQLAlchemyError as e:
        print(f"Error: {e}")

def add_multiple_columns(engine, table_name: str, column_names: List[str], column_types: Union[str, List[str]]):
    """
    Add multiple columns to an existing table.


    :param engine: SQLAlchemy engine connected to the database.
    :param table_name: Name of the table to which columns will be added.
    :param column_names: A list of column names (list of strings).
    :param column_types: sql type to apply to the added columns, either a single type (string) or a list of types (list of strings).
    """
    try:
        # Convert single string to list if necessary
        if isinstance(column_types, str):
            column_types = [column_types] * len(column_names)

        with Session(engine) as session:
            for column_name, type in zip(column_names, column_types):
                # Compile the column type for the specific database dialect
                # Execute the ALTER TABLE command
                stmt = text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {type}')
                session.execute(stmt)
                print(f"Column {column_name} added successfully.")

            session.commit()
            print(f"Columns commited successfully.")
    except SQLAlchemyError as e:
        print(f"Error: {e}")

def remove_column(engine, table_name, column_name):
    try:
        # Execute the ALTER TABLE command to drop the column
        stmt = text(f'ALTER TABLE {table_name} DROP COLUMN {column_name}')
        with engine.connect() as connection:
            connection.execute(stmt)
            print(f"Column {column_name} removed successfully.")
    except SQLAlchemyError as e:
        print(f"Error: {e}")

# function to retrieve data from the databse
def find_entries(session, table_class, **kwargs):
    """
    Check if an entry exists in the table based on given parameters.

    :param engine: SQLAlchemy engine connected to the database.
    :param table_class: The ORM class representing the table.
    :param kwargs: Column-value pairs to filter the query.
    :return: True if the entry exists, False otherwise.
    """
    try:
        query = select(table_class).filter_by(**kwargs)
        result = session.scalars(query).all()
        return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return []

def get_column_value_pairs(orm_object):
    """
    Retrieve column-value pairs from an SQLAlchemy ORM object as a dictionary.

    :param orm_object: The SQLAlchemy ORM object.
    :return: A dictionary containing column-value pairs.
    """
    table_class = type(orm_object)
    column_value_pairs = {column.name: getattr(orm_object, column.name) for column in table_class.__table__.columns}
    return column_value_pairs

def get_result_path_from_ids(session, experiment_id, eeg_id):
    """
    Retrieve the result path from the ResultAssociation table based on experiment_id and eeg_id.

    :param session: SQLAlchemy session object.
    :param experiment_id: ID of the experiment.
    :param eeg_id: ID of the EEG.
    :return: The result path if found, None otherwise.
    """
    results = find_entries(session, ResultAssociation, experiment_id=experiment_id, eeg_id=eeg_id)
    if results:
        return results[0].result_path
    else:
        return None

# function to add data to the database
def add_metric_data_table(con, experiment_id: str, eeg_id: str, df: pd.DataFrame, table_exists='append'):
    """
    Add metric data to the database for a specific experiment and EEG.
    Creates a table named 'data_experiment_{experiment_id}_eeg_{eeg_id}'.

    Parameters:
    - engine: SQLAlchemy engine or connection
    - experiment_id: ID of the experiment
    - eeg_id: ID of the EEG
    - df: DataFrame containing channel data
    - table_exists: Action to take if the table already exists ('append', 'replace')
    """
    try:
        # if con is a session, get the connection
        if isinstance(con, Session):
            con = con.connection()

        # Create table name
        table_name = f"data_experiment_{experiment_id}"

        # Add experiment_id and eeg_id as columns to the DataFrame
        df_with_ids = df.copy()
        df_with_ids['eeg_id'] = eeg_id

        # Reorder columns to have IDs first
        cols = ['eeg_id'] + [col for col in df_with_ids.columns if
                                          col not in ['experiment_id', 'eeg_id']]
        df_new = df_with_ids[cols]

        # Make sure data is appended and unique
        if table_exists == 'append':
            try:
                df_old = pd.read_sql_table(table_name, con)
                df_merged = pd.concat([df_old, df_new], ignore_index=True)
                df_merged_unique = df_merged.drop_duplicates().reset_index(drop=True)
                print(f"Table {table_name} exist, appending new rows to existing table")
            except ValueError:
                print(f"Table {table_name} does not exist, creating new table")
                df_merged_unique = df_new
            except Exception as e:
                print(f"Error reading existing table: {e}")
                return None
        elif table_exists == 'replace':
            df_merged_unique = df_new
        else:
            print(f'table_exists argument {table_exists} is not valid, must be either append or replace')
            return None

        # Add data to SQL database
        df_merged_unique.to_sql(
            name=table_name,
            con=con,
            if_exists='replace',  # 'replace' will drop and recreate the table if it exists
            index=False  # Include the index as a column
        )

        print(f"Successfully created and populated table: {table_name}")
        return table_name

    except Exception as e:
        print(f"Error creating metric data table: {e}")
        return None

def add_or_update_eeg_entry(session, dataset_id, filepath, filename, file_extension):
    """
    Initialize or retrieve an EEG entry in the database.

    Parameters:
    - sqlpath: Path to the SQLite database
    - dataset_id: ID of the dataset this EEG belongs to
    - filepath: Path to the EEG file
    - filename: Name of the EEG file (without extension)
    - file_extension: Extension of the EEG file

    Returns:
    - eeg_id: The id of the EEG object that was created or retrieved
    """
    # Check if the EEG already exists in the database
    matching_eegs = find_entries(session, EEG,
                                dataset_id=dataset_id,
                                filename=filename,
                                filepath=filepath,
                                filetype=file_extension)
    if len(matching_eegs) == 0:
        eeg = EEG(id=str(uuid.uuid4().hex),
                 filename=filename,
                 dataset_id=dataset_id,
                 filepath=filepath,
                 filetype=file_extension)
        session.add(eeg)
        print(f"Created new EEG entry: {filename}")
    elif len(matching_eegs) == 1:
        print(f"Found matching EEG in the dataset: {filename}")
        eeg = matching_eegs[0]
    else:
        print(f"Multiple EEGs in the dataset that match {filename}, please manually check")
        return None
    session.commit()
    return eeg

def add_or_update_experiment(session, metric_set_name, run_name, fs=None,
                        start=None, stop=None, lower_cutoff=None, upper_cutoff=None, window_len=None, window_overlap=None, montage=None):
    """
    Initialize or retrieve a MetricSet entry in the database.

    Parameters:
    - sqlpath: Path to the SQLite database
    - eeg_id: ID of the EEG this metric set belongs to
    - metric_set_name: Name of the metric set
    - signal_len: Length of the signal in samples
    - fs: Sampling frequency
    - lfreq: Lower cutoff frequency for filtering
    - hfreq: Upper cutoff frequency for filtering
    - ep_dur: Duration of each epoch in seconds
    - ep_overlap: Overlap between epochs in seconds
    - montage: Montage used for the EEG

    Returns:
    - MetricSet: The MetricSet object that was created or retrieved
    """
    # Check if metric set already exists for this EEG
    matching_experiments = find_entries(
        session,
        Experiment,
        metric_set_name=metric_set_name,
        run_name=run_name,
    )

    if len(matching_experiments) == 0:
        experiment = Experiment(
            metric_set_name=metric_set_name,
            run_name=run_name,
            fs=fs,
            start=start,
            stop=stop,
            window_len=window_len,
            window_overlap=window_overlap,
            lower_cutoff=lower_cutoff,
            upper_cutoff=upper_cutoff,
            montage=montage
        )
        session.add(experiment)
        session.commit()
        print(f"Created new metric set: {metric_set_name}")
        return experiment
    elif len(matching_experiments) == 1:
        print(f"Found existing metric set: {metric_set_name}")
        return matching_experiments[0]
    else:
        raise ValueError(f"Multiple metric sets found for {metric_set_name}")

def add_or_update_dataset(session, dataset_name, dataset_path, dataset_description):
    """
    Add or update a dataset in the database.

    Parameters:
    - sqlpath: Path to the SQLite database
    - dataset_name: Name of the dataset
    - dataset_path: Path to the dataset
    - dataset_description: Description of the dataset

    Returns:
    - DataSet: The dataset object that was created or retrieved
    """
    # Add a dataset to the sqlite database
    # Check if the dataset already exists in our database
    matching_datasets = find_entries(session, DataSet, name=dataset_name, path=dataset_path)
    if len(matching_datasets) == 0:
        dataset = DataSet(id=str(uuid.uuid4().hex), name=dataset_name, path=dataset_path, description=dataset_description)
        session.add(dataset)
        print(f"Created new dataset: {dataset_name}")
    elif len(matching_datasets) == 1:
        print(f"Found matching dataset in database, updating description if necessary")
        dataset = matching_datasets[0]
        dataset.description = dataset_description
    else:
        print('Multiple datasets in the database that match name and path, please manually check')
        return None
    session.commit()
    return dataset

def add_result_path(session, experiment_id, eeg_id, result_path):
    matching_results = find_entries(session, ResultAssociation, experiment_id=experiment_id, eeg_id=eeg_id)
    if len(matching_results) == 0:
        print('No result found for experiment and eeg, please ensure experiment and eeg are in the database')
        return None
    elif len(matching_results) == 1:
        matching_results[0].result_path = result_path
        session.commit()
        return matching_results[0]
    else:
        print('Multiple results in the database that match experiment and eeg, please manually check')
        return None

def initialize_tables(path=None, path_is_relative=True):
    if path:
        if path_is_relative:
            engine = create_engine(f"sqlite+pysqlite:///{path}")
        else:
            engine = create_engine(f"sqlite+pysqlite:////{path}")
    else:
        engine = create_engine("sqlite+pysqlite://:memory:")
    Base.metadata.create_all(bind=engine)
    return engine

# functions to test functionality

def test_adding_data(db_path):
    """Test the data addition pipeline with a sample EEG dataset and metrics."""
    # Define the metric name first (needed for metric set creation)
    engine = initialize_tables(db_path)

    with Session(engine) as session:
        # 1. Create a test dataset
        dataset = add_or_update_dataset(
            session,
            dataset_name='EEG Study Dataset',
            dataset_path='/data/eeg_study',
            dataset_description='Dataset for EEG study on cognitive functions'
        )
        # 2. Create a test EEG entry
        eeg = add_or_update_eeg_entry(
            session,
            dataset_id=dataset.id,
            filepath='/data/eeg_study',
            filename='subject_01_session_01',
            file_extension='.edf'
        )
        # 3. Create a test metric set
        result_path = '/results/alpha_power'
        experiment = add_or_update_experiment(
            session,
            metric_set_name='Alpha power',
            run_name='low_freq',
            fs=250,          # Sample frequency
            lower_cutoff=8,         # Alpha band lower cutoff
            upper_cutoff=13,        # Alpha band upper cutoff
            window_len=4,        # 4-second epochs
            window_overlap=2     # 2-second overlap
        )
        if not eeg in experiment.eegs:
            experiment.eegs.append(eeg)

        add_result_path(session, experiment.id, eeg.id, result_path)

        # 4. Create sample channel data as a DataFrame
        channel_data = pd.DataFrame({
            'Fp1': [0.75, 1],
            'Fp2': [0.82, 2.5],
            'F3': [0.65, 4.5],
            'F4': [0.71, 6]
        })

        # 5. Add the channel data to the database
        add_metric_data_table(
            con=session.connection(),
            experiment_id=experiment.id,
            eeg_id=eeg.id,
            df=channel_data
        )
        session.commit()
        print("Test data added successfully.")

if __name__ == "__main__":
    # Run the test functions
    print("Running database tests...")
    db_path = 'test.sqlite'
    test_adding_data(db_path)
    print("All tests completed successfully.")