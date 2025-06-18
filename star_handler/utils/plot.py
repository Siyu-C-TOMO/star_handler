"""
Visualization utilities for particle analysis.

This module provides plotting functions for:
- Histograms (angles, distances, cluster sizes)
- KDE plots
- Polar plots
- XY scatter plots
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from scipy.stats import gaussian_kde
from typing import Optional, Tuple
import warnings

class PlotError(Exception):
    """Base exception for plotting operations."""
    pass

def plot_histogram(data: np.ndarray,
                  name: str,
                  plot_type: str = 'angle',
                  title: Optional[str] = None,
                  xlabel: Optional[str] = None,
                  ylabel: Optional[str] = None) -> None:
    """Create histogram for distribution data.
    
    [WORKFLOW]
    1. Configure plot based on type
    2. Generate histogram
    3. Add peaks for angle data
    4. Save figure
    
    [PARAMETERS]
    data : np.ndarray
        Data to plot
    name : str
        Output file name (without extension)
    plot_type : str
        Type of plot ('angle', 'distance', or 'cluster')
    title, xlabel, ylabel : Optional[str]
        Plot labels
        
    [RAISES]
    PlotError
        If plotting fails
        
    [EXAMPLE]
    >>> plot_histogram(angles, 'orientation_dist', 'angle')
    """
    try:
        plt.figure(figsize=(10, 6))
        
        # Configure based on type
        if plot_type == 'angle':
            bins = np.arange(0, 183, 3)
            title = title or 'Distribution of Orientation Angles'
            xlabel = xlabel or 'Angle (degrees)'
        elif plot_type == 'distance':
            bins = 'auto'
            title = title or 'Distribution of Particle Distances'
            xlabel = xlabel or 'Distance (Å)'
        elif plot_type == 'cluster':
            max_size = int(np.max(data))
            bins = np.arange(1, max_size + 2) - 0.5
            title = title or 'Distribution of Cluster Sizes'
            xlabel = xlabel or 'Cluster Size'
        else:
            raise ValueError(f"Unknown plot type: {plot_type}")
            
        ylabel = ylabel or 'Frequency'
        
        # Create histogram
        hist, bins, _ = plt.hist(data,
                                bins=bins,
                                edgecolor='black',
                                color='blue',
                                alpha=0.7)
                                
        # Add peaks for angle distribution
        if plot_type == 'angle':
            peaks, _ = find_peaks(hist, prominence=10)
            peak_pos = [(bins[i] + bins[i+1])/2 for i in peaks]
            for pos in peak_pos:
                plt.axvline(pos, 
                           color='red',
                           linestyle='--',
                           alpha=0.5)
                
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        
        # Save plot
        plt.savefig(f"{name}.jpg", dpi=300, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        raise PlotError(f"Histogram plotting failed: {str(e)}")

def plot_kde(data: np.ndarray,
            name: str,
            bandwidth: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Create KDE plot with peak detection.
    
    [WORKFLOW]
    1. Calculate KDE
    2. Detect peaks
    3. Create combined plot
    
    [PARAMETERS]
    data : np.ndarray
        Data for KDE
    name : str
        Output file name
    bandwidth : Optional[float]
        KDE bandwidth parameter
        
    [OUTPUT]
    Tuple[np.ndarray, np.ndarray]:
        - x values
        - KDE values
        
    [RAISES]
    PlotError
        If KDE plotting fails
        
    [EXAMPLE]
    >>> x, kde = plot_kde(angles, 'angle_density')
    """
    try:
        if isinstance(data, pd.Series):
            data = data.to_numpy()
            
        # Calculate KDE
        kde = gaussian_kde(data.flatten(), bw_method=bandwidth)
        x = np.linspace(data.min(), data.max(), 1000)
        pdf = kde.evaluate(x)
        
        # Find peaks
        peaks, _ = find_peaks(pdf, prominence=0.05)
        
        # Create plot
        plt.figure(figsize=(10, 6))
        plt.plot(x, pdf, label='KDE', color='blue')
        plt.scatter(x[peaks],
                   pdf[peaks],
                   color='red',
                   s=60,
                   label='Peaks')
                   
        plt.hist(data,
                bins=np.arange(0, 183, 3),
                density=True,
                alpha=0.3,
                color='gray',
                label='Data')
                
        plt.title('Kernel Density Estimation')
        plt.xlabel('Value')
        plt.ylabel('Density')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.savefig(f"{name}.jpg", dpi=300, bbox_inches='tight')
        plt.close()
        
        return x, pdf
        
    except Exception as e:
        raise PlotError(f"KDE plotting failed: {str(e)}")

def plot_polar(data: np.ndarray,
              name: str,
              bin_width: float = 3.0) -> None:
    """Create polar histogram for angular data.
    
    [WORKFLOW]
    1. Configure polar plot
    2. Create histogram
    3. Add colorbar
    
    [PARAMETERS]
    data : np.ndarray
        Angular data (0-90 degrees)
    name : str
        Output file name
    bin_width : float
        Width of angular bins
        
    [RAISES]
    PlotError
        If polar plotting fails
        
    [EXAMPLE]
    >>> plot_polar(angles, 'angle_polar')
    """
    try:
        # Configure style
        plt.rcParams.update({'font.size': 12})
        cmap = 'gist_heat_r'
        
        # Setup bins
        theta_edges_deg = np.arange(0, 93, bin_width)
        theta_edges_rad = np.deg2rad(theta_edges_deg)
        r_edges = [0, 90]
        
        # Create histogram
        hist, _ = np.histogram(data, bins=theta_edges_deg)
        
        # Create polar plot
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection='polar')
        
        # Configure polar parameters
        ax.set_thetamin(0)
        ax.set_thetamax(90)
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(1)
        
        # Remove radial labels
        ax.set_yticklabels([])
        ax.spines['polar'].set_visible(False)
        
        # Create mesh
        Theta, R = np.meshgrid(theta_edges_rad, r_edges)
        C = hist.reshape(1, -1)
        
        # Plot heatmap
        mesh = ax.pcolormesh(Theta,
                           R,
                           C,
                           shading='flat',
                           cmap=cmap)
                           
        # Add colorbar
        cbar = fig.colorbar(mesh,
                           orientation='horizontal',
                           pad=0.2,
                           aspect=30)
        cbar.set_label('Frequency', fontsize=12)
        
        plt.title('Angular Distribution (0-90°)',
                 pad=20,
                 fontsize=14)
                 
        plt.savefig(f"{name}.jpg", dpi=300, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        raise PlotError(f"Polar plotting failed: {str(e)}")

def plot_xy(file_name: str,
           output_path: Optional[str] = None,
           xlabel: Optional[str] = None,
           ylabel: Optional[str] = None,
           smooth: bool = False) -> None:
    """Create scatter plot from tabulated data.
    
    [WORKFLOW]
    1. Read data file
    2. Create scatter plot
    3. Add smoothed line (optional)
    
    [PARAMETERS]
    file_name : str
        Input data file path
    output_path : Optional[str]
        Output plot path
    xlabel, ylabel : Optional[str]
        Axis labels
    smooth : bool
        Whether to add smoothed line
        
    [RAISES]
    PlotError
        If plotting fails
        
    [EXAMPLE]
    >>> plot_xy('data.txt', 'plot.png', 'X', 'Y')
    """
    try:
        # Read data
        results_df = pd.read_csv(file_name, sep='\t')
        x_col, y_col = results_df.columns[:2]
        
        # Create plot
        plt.figure(figsize=(10, 6))
        
        # Scatter plot
        plt.scatter(results_df[x_col],
                   results_df[y_col],
                   color='blue',
                   alpha=0.3,
                   s=20)
                   
        # Add smoothed line
        if smooth:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                try:
                    window = min(51, len(results_df) - 1)
                    if window % 2 == 0:
                        window -= 1
                    y_smooth = savgol_filter(results_df[y_col],
                                           window,
                                           3)
                    plt.plot(results_df[x_col],
                            y_smooth,
                            color='red',
                            linewidth=2)
                except Exception:
                    pass
                    
        # Configure plot
        plt.title(f'{y_col} vs {x_col}')
        plt.xlabel(xlabel or x_col)
        plt.ylabel(ylabel or y_col)
        plt.grid(True, alpha=0.3)
        
        # Save plot
        output_file = output_path or 'plot.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        raise PlotError(f"XY plotting failed: {str(e)}")
