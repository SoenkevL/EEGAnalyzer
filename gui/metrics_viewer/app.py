"""
Main application class for the EEG Metrics Viewer.
"""

import os
import sys
import customtkinter as ctk

from .database_handler import DatabaseHandler
from .plot_frame import MetricsPlotFrame
from .selection_frame import SelectionFrame


class App(ctk.CTk):
    """
    Main application class for the EEG Metrics Viewer.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the application.
        
        Args:
            db_path: Path to the SQLite database file
        """
        super().__init__()
        
        # Configure window
        self.title("EEG Metrics Viewer")
        self.geometry("1400x800")  # Larger default size
        
        # Configure grid layout - give much more space to the plot
        self.grid_columnconfigure(0, weight=1)    # Selection panel
        self.grid_columnconfigure(1, weight=5)    # Plot area (significantly increased weight)
        self.grid_rowconfigure(0, weight=1)
        
        # Initialize database handler
        self.db_handler = DatabaseHandler(db_path)
        
        # Create plot frame with more space
        self.plot_frame = MetricsPlotFrame(self, title="Metrics Visualization")
        self.plot_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        
        # Create selection frame with narrower fixed width
        self.selection_frame = SelectionFrame(self, self.db_handler, self.plot_frame, width=150)
        self.selection_frame.grid_propagate(False)  # Prevent the frame from resizing based on content
