# -*- coding: utf-8 -*-
"""12/8/24 Data Analysis on ticker data.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1nOJDlm7sVtboa9YP_jZynH_nfBE2bS9d

# Imports, GPU memory mang
"""

# Cell 1: Imports and Setup
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
from pathlib import Path
import torch
import cudf
import numpy as np
from tqdm.auto import tqdm
import gc
from google.colab import drive
from sklearn.preprocessing import MinMaxScaler

# Check GPU availability and print info
print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

"""# Data directory Config

"""

# Cell 2: Mount Drive and Setup Directories
print("Mounting Google Drive...")
drive.mount('/content/drive')

DATA_DIR = '/content/drive/My Drive/data for training/NVDA data'

if not os.path.exists(DATA_DIR):
    raise ValueError(f"Directory not found: {DATA_DIR}")
else:
    print(f"Successfully accessed directory: {DATA_DIR}")
    print(f"Files found: {len(list(Path(DATA_DIR).glob('*.csv')))}")

"""# Config File for everything else"""

class Config:
    # Data Processing Settings
    CSV_COLUMNS = [
        'ts_recv', 'ts_event', 'rtype', 'publisher_id', 'instrument_id',
        'action', 'side', 'depth', 'price', 'size', 'flags',
        'ts_in_delta', 'sequence', 'symbol'
    ]

    # Time Settings
    TRAIN_START_DATE = "2018-05-02T08:44:39.292059872Z"
    TRAIN_END_DATE = "2024-10-21T08:00:00.143369486Z"
    TEST_START_DATE = "2024-03-07T09:00:00.785957501Z"
    TEST_END_DATE = "2024-10-21T23:59:51.581176405Z"

    # Stock Split Information
    SPLITS_INFO = [
        ('2021-07-20T00:00:00Z', 4.0),
        ('2024-06-10T00:00:00Z', 10.0)
    ]

    # Visualization Settings
    PLOT_FIGSIZE = (15, 20)
    DOWNSAMPLE_TARGET_POINTS = 10000
    HISTOGRAM_BINS = 50
    PLOT_ALPHA = 0.7
    SPLIT_LINE_COLORS = ['g', 'purple']

    # Data Scaling Settings
    SCALER_BUFFER_FACTOR = 0.1
    SCALER_FEATURE_RANGE = (0, 1)

    # Volatility Settings
    VOLATILITY_RESAMPLE_FREQ = 'H'

    # Progress Bar Settings
    DATA_PROCESSING_STEPS = 7
    VISUALIZATION_STEPS = 6

    # Stock Settings
    TICKER_SYMBOL = 'NVDA'

    # Debug and Verification Settings
    TEST_PRICE_POINTS = np.array([[50.0], [100.0], [150.0]])
    SAMPLE_SCALE_POINTS = np.array([[0.5], [1.0]])

    # Log Transform Settings
    LOG_BASE = np.e  # natural log
    LOG_EPSILON = 1e-10  # small constant to avoid log(0)

# Create color schemes for consistent plotting
class PlotColors:
    TRAINING = 'blue'
    TESTING = 'red'
    VOLATILITY = 'green'
    SPLIT_LINES = ['red', 'purple']

# Create standardized plot labels
class PlotLabels:
    class TimeSeries:
        ADJUSTED = 'NVDA Split-Adjusted Price Time Series'
        UNADJUSTED = 'NVDA Unadjusted Price Time Series'
        X_LABEL = 'Time'
        Y_LABEL = 'Price ($)'

    class Distribution:
        ADJUSTED = 'Split-Adjusted Price Distribution'
        UNADJUSTED = 'Unadjusted Price Distribution'
        X_LABEL = 'Price ($)'
        Y_LABEL = 'Count'

    class Returns:
        TITLE = 'Daily Returns Distribution'
        X_LABEL = 'Daily Return (%)'
        Y_LABEL = 'Count'

    class Volatility:
        TITLE = 'Hourly Price Volatility'
        X_LABEL = 'Date'
        Y_LABEL = 'Standard Deviation'

# Add to PlotLabels class:
class PlotLabels:
    class LogTimeSeries:
        ADJUSTED = 'NVDA Log-Transformed Price Time Series'
        X_LABEL = 'Time'
        Y_LABEL = 'Log Price'

    class LogDistribution:
        ADJUSTED = 'Log-Transformed Price Distribution'
        X_LABEL = 'Log Price'
        Y_LABEL = 'Count'

    class LogReturns:
        TITLE = 'Log-Transformed Daily Returns Distribution'
        X_LABEL = 'Log Return (%)'
        Y_LABEL = 'Count'

    class LogVolatility:
        TITLE = 'Log-Transformed Price Volatility'
        X_LABEL = 'Date'
        Y_LABEL = 'Log Standard Deviation'

# Error Messages
class ErrorMessages:
    DIR_NOT_FOUND = "Directory not found: {}"
    NO_FILES_READ = "No files were successfully read from the directory"
    FILE_READ_ERROR = "Error reading {}: {}"
    SPLIT_DATA_ERROR = "Error fetching split data: {}"

# Create a config instance for easy access
config = Config()
plot_colors = PlotColors()
plot_labels = PlotLabels()
error_msgs = ErrorMessages()

"""# Split History via Yfinance"""

# Cell: Stock Split History
def get_split_history(ticker=config.TICKER_SYMBOL,
                     start=config.TRAIN_START_DATE,
                     end=config.TRAIN_END_DATE):
    """Get historical stock splits data for a given ticker."""
    try:
        # Get stock splits data
        stock = yf.Ticker(ticker)
        splits = stock.splits.loc[start:end]

        # Display results
        if not splits.empty:
            for date, ratio in splits.items():
                print(f"Split on {date.date()}: {ratio}:1 ratio")
            return splits

        print(f"No stock splits found for {ticker}")
        return pd.Series()

    except Exception as e:
        print(f"Error fetching split data: {e}")
        return pd.Series()

# Get NVDA splits
splits = get_split_history()

"""# GPU data loading"""

# Cell: GPU Data Loading
def read_and_combine_csv_files_gpu(directory_path=DATA_DIR):
   """Load and combine CSV files using GPU acceleration"""
   dfs = []
   files = list(Path(directory_path).glob('*.csv'))

   # Read files
   for file in tqdm(files, desc="Reading CSVs"):
       try:
           df = cudf.read_csv(file,
                            skiprows=1,
                            names=config.CSV_COLUMNS,
                            skipinitialspace=True)

           # Show sample data for first file
           if len(dfs) == 1:
               print("\nSample data:")
               print(df.head())
               print("\nColumn types:")
               print(df.dtypes)

           dfs.append(df)

       except Exception as e:
           print(f"Error reading {file.name}: {e}")

   if not dfs:
       raise ValueError(error_msgs.NO_FILES_READ)

   # Process data
   with tqdm(total=3, desc="Processing data") as pbar:
       # Combine dataframes
       combined_df = cudf.concat(dfs, ignore_index=True)
       pbar.update(1)

       # Convert timestamps
       combined_df['ts_event'] = cudf.to_datetime(combined_df['ts_event'])
       pbar.update(1)

       # Print summary
       print(f"\nProcessed {len(dfs)} files, {len(combined_df):,} total rows")
       print(f"Time range: {combined_df['ts_event'].min()} to {combined_df['ts_event'].max()}")
       pbar.update(1)

   return combined_df

# Load data
df = read_and_combine_csv_files_gpu()

"""# Stock split adjustment"""

# Cell: Split Adjustment
def adjust_for_splits(df):
    """Adjust price data for stock splits"""
    adjusted_df = df.copy()

    # Process timestamps and sort data
    adjusted_df = adjusted_df.sort_values('ts_event')

    # Convert to pandas for easier timezone handling
    adjusted_df = adjusted_df.to_pandas()
    adjusted_df.set_index('ts_event', inplace=True)

    # Localize timezone if needed
    if adjusted_df.index.tz is None:
        adjusted_df.index = adjusted_df.index.tz_localize('UTC')

    # Apply split adjustments
    for split_date, ratio in config.SPLITS_INFO:
        split_datetime = pd.to_datetime(split_date)
        if split_datetime.tz is None:
            split_datetime = split_datetime.tz_localize('UTC')

        mask = adjusted_df.index < split_datetime
        adjusted_df.loc[mask, 'price'] = adjusted_df.loc[mask, 'price'] / ratio

    print("\nSplit Adjustment Summary:")
    print(f"Time range: {adjusted_df.index.min()} to {adjusted_df.index.max()}")
    print(f"Price range: {adjusted_df['price'].min():.2f} to {adjusted_df['price'].max():.2f}")

    return adjusted_df

# Apply split adjustment
df_adjusted = adjust_for_splits(df)

"""# Daily Returns statistics"""

# Cell: Daily Returns Calculation
def calculate_daily_returns(df):
    """Calculate daily returns from adjusted prices"""
    df = df.copy()
    df['date'] = df.index.date
    daily_prices = df.groupby('date')['price'].last()
    returns = daily_prices.pct_change()

    # Create DataFrame with returns
    daily_returns_df = pd.DataFrame({
        'date': returns.index,
        'returns': returns.values
    })
    daily_returns_df.set_index('date', inplace=True)

    print(f"Daily returns range: {returns.min()*100:.2f}% to {returns.max()*100:.2f}%")
    return daily_returns_df

import numpy as np
from scipy import stats

def analyze_returns_statistics(daily_returns_df, risk_free_rate=0.01):
    """
    Perform detailed statistical analysis on daily returns.

    Parameters:
    - daily_returns_df (DataFrame): DataFrame with a column named 'returns'.
    - risk_free_rate (float): Annualized risk-free rate, default is 0.01 (1%).

    Returns:
    - stats_dict (dict): Basic statistics of returns.
    - risk_metrics_dict (dict): Risk-related metrics of returns.
    """
    if 'returns' not in daily_returns_df.columns:
        raise ValueError("The input DataFrame must contain a 'returns' column.")

    returns = daily_returns_df['returns'].dropna()

    if returns.empty:
        raise ValueError("The 'returns' column contains no valid data.")

    # Basic statistics
    stats_dict = {
        'Mean (%)': returns.mean() * 100,
        'Median (%)': returns.median() * 100,
        'Std Dev (%)': returns.std() * 100,
        'Skewness': returns.skew(),
        'Kurtosis': returns.kurtosis(),
        'Min (%)': returns.min() * 100,
        'Max (%)': returns.max() * 100
    }

    # Risk metrics
    negative_returns = returns[returns < 0]
    positive_returns = returns[returns > 0]

    # Value at Risk (VaR)
    var_95 = np.percentile(returns, 5) * 100
    var_99 = np.percentile(returns, 1) * 100

    # Sharpe Ratio
    annualized_return = returns.mean() * 252
    annualized_volatility = returns.std() * np.sqrt(252)
    sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility > 0 else np.nan

    risk_metrics_dict = {
        'Value at Risk 95% (%)': var_95,
        'Value at Risk 99% (%)': var_99,
        'Positive Days (%)': (len(positive_returns) / len(returns)) * 100,
        'Negative Days (%)': (len(negative_returns) / len(returns)) * 100,
        'Avg Positive Return (%)': positive_returns.mean() * 100 if not positive_returns.empty else 0,
        'Avg Negative Return (%)': negative_returns.mean() * 100 if not negative_returns.empty else 0,
        'Sharpe Ratio': sharpe_ratio
    }

    # Perform Jarque-Bera test for normality
    jb_stat, jb_pvalue = stats.jarque_bera(returns)
    jb_test_results = {
        'JB Statistic': jb_stat,
        'P-value': jb_pvalue,
        'Normal Distribution': 'Rejected' if jb_pvalue < 0.05 else 'Not Rejected'
    }

    # Print results in a structured format
    print("\n--- Basic Statistics ---")
    for metric, value in stats_dict.items():
        print(f"{metric:<20}: {value:>8.3f}")

    print("\n--- Risk Metrics ---")
    for metric, value in risk_metrics_dict.items():
        print(f"{metric:<20}: {value:>8.3f}")

    print("\n--- Jarque-Bera Test ---")
    for metric, value in jb_test_results.items():
        print(f"{metric:<20}: {value}")

    return stats_dict, risk_metrics_dict, jb_test_results

# Example usage
daily_returns_df = calculate_daily_returns(df_adjusted)  # Replace with your DataFrame
stats, risk_metrics, jb_results = analyze_returns_statistics(daily_returns_df)

"""# downsampling the data, to make the graphs easier to read"""

# Cell: Data Downsampling
def downsample_for_plotting(df, target_points=config.DOWNSAMPLE_TARGET_POINTS):
    """Downsample data for visualization"""
    if len(df) > target_points:
        sample_interval = len(df) // target_points
        return df.iloc[::sample_interval]
    return df

# Create downsampled version for plotting
df_downsampled = downsample_for_plotting(df_adjusted)

"""# Normalizing data to 0 through 1 with a 10% scaler buffer"""

# Cell: Data Scaling
def scale_data(df, buffer_factor=config.SCALER_BUFFER_FACTOR):
    """Scale the split-adjusted price data"""
    # Prepare data
    price_data = df['price'].values.reshape(-1, 1)

    # Calculate range with buffer
    data_min = price_data.min()
    data_max = price_data.max()
    range_size = data_max - data_min
    buffer = range_size * buffer_factor
    feature_range = (data_min - buffer, data_max + buffer)

    # Scale data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(np.array([[feature_range[0]], [feature_range[1]]]))
    scaled_data = scaler.transform(price_data)

    # Print summary
    print("\nScaling Summary:")
    print(f"Original price range: {data_min:.2f} to {data_max:.2f}")
    print(f"Buffer range: {feature_range[0]:.2f} to {feature_range[1]:.2f}")
    print(f"Scaled range: {scaled_data.min():.4f} to {scaled_data.max():.4f}")

    return scaled_data, scaler

# Scale the adjusted data
scaled_data, scaler = scale_data(df_adjusted)

# Cell: Scale Verification
def verify_scaling(scaler):
    """Verify scaler with sample points"""
    # Test standard scaling points
    sample_points = config.SAMPLE_SCALE_POINTS
    sample_restored = scaler.inverse_transform(sample_points)

    print("Standard Scale Test:")
    for scale, orig in zip(sample_points.flatten(), sample_restored.flatten()):
        print(f"Scaled {scale:.4f} -> Original {orig:.4f}")

    # Test specific price points
    test_prices = config.TEST_PRICE_POINTS
    scaled = scaler.transform(test_prices)
    restored = scaler.inverse_transform(scaled)

    print("\nPrice Point Test:")
    for orig, scale, rest in zip(test_prices.flatten(), scaled.flatten(), restored.flatten()):
        print(f"Original {orig:.2f} -> Scaled {scale:.4f} -> Restored {orig:.2f}")

# Verify scaling
verify_scaling(scaler)

"""# Normalizing data using split adjusted data that has been Logarithmically transformed."""

# log transformation
def log_transform_data(df, log_base=config.LOG_BASE, epsilon=config.LOG_EPSILON):
    """Log transform the split-adjusted price data"""
    # Prepare data
    price_data = df['price'].values.reshape(-1, 1)

    # Apply log transform
    log_data = np.log(price_data + epsilon) / np.log(log_base)

    # Create new DataFrame with log prices
    df_logged = df.copy()
    df_logged['price'] = log_data

    # Print summary
    print("\nLog Transform Summary:")
    print(f"Original price range: {price_data.min():.2f} to {price_data.max():.2f}")
    print(f"Log price range: {log_data.min():.4f} to {log_data.max():.4f}")

    return df_logged

# Log transform the adjusted data
df_logged = log_transform_data(df_adjusted)

# Scale the log-transformed data
scaled_data, scaler = scale_data(df_logged)

"""# Visualizations for split adjusted data, data before split adjustment, and statistics on daily returns"""

# Cell: Visualization
def visualize_price_data(df_adjusted, df_downsampled, daily_returns):
    """Create comprehensive price visualization plots"""
    plt.figure(figsize=config.PLOT_FIGSIZE)

    # Plot 1: Split-adjusted prices
    plt.subplot(4, 1, 1)
    plt.plot(df_downsampled.index, df_downsampled['price'],
            color=plot_colors.TRAINING,
            label=f'{config.TICKER_SYMBOL} Adjusted Price',
            alpha=config.PLOT_ALPHA)

    # Add split lines
    for (split_date, ratio), color in zip(config.SPLITS_INFO, plot_colors.SPLIT_LINES):
        split_datetime = pd.to_datetime(split_date)
        if split_datetime.tz is None:
            split_datetime = split_datetime.tz_localize('UTC')
        plt.axvline(x=split_datetime, color=color, linestyle='--',
                   label=f'Split ({ratio}:1)', alpha=config.PLOT_ALPHA)
    plt.title(plot_labels.TimeSeries.ADJUSTED)
    plt.xlabel(plot_labels.TimeSeries.X_LABEL)
    plt.ylabel(plot_labels.TimeSeries.Y_LABEL)
    plt.legend()
    plt.grid(True)

    # Plot 2: Price distribution
    plt.subplot(4, 1, 2)
    plt.hist(df_downsampled['price'],
            bins=config.HISTOGRAM_BINS,
            alpha=config.PLOT_ALPHA,
            color=plot_colors.TRAINING)
    plt.title(plot_labels.Distribution.ADJUSTED)
    plt.xlabel(plot_labels.Distribution.X_LABEL)
    plt.ylabel(plot_labels.Distribution.Y_LABEL)

    # Plot 3: Daily returns distribution
    plt.subplot(4, 1, 3)
    plt.hist(daily_returns,
            bins=config.HISTOGRAM_BINS,
            alpha=config.PLOT_ALPHA,
            color=plot_colors.TRAINING)
    plt.title(plot_labels.Returns.TITLE)
    plt.xlabel(plot_labels.Returns.X_LABEL)
    plt.ylabel(plot_labels.Returns.Y_LABEL)
    plt.grid(True)

    # Plot 4: Volatility
    plt.subplot(4, 1, 4)
    vol_df = df_adjusted.copy()
    vol_df = vol_df.resample(config.VOLATILITY_RESAMPLE_FREQ).agg({'price': ['std']}).dropna()
    vol_df_plot = downsample_for_plotting(vol_df)

    plt.plot(vol_df_plot.index, vol_df_plot['price']['std'],
            color=plot_colors.VOLATILITY)

    # Add split lines to volatility plot
    for (split_date, ratio), color in zip(config.SPLITS_INFO, plot_colors.SPLIT_LINES):
        split_datetime = pd.to_datetime(split_date)
        if split_datetime.tz is None:
            split_datetime = split_datetime.tz_localize('UTC')
        plt.axvline(x=split_datetime, color=color, linestyle='--',
                   alpha=config.PLOT_ALPHA/2)
    plt.title(plot_labels.Volatility.TITLE)
    plt.xlabel(plot_labels.Volatility.X_LABEL)
    plt.ylabel(plot_labels.Volatility.Y_LABEL)
    plt.grid(True)

    plt.tight_layout()
    plt.show()

    # Print statistics summary
    print(f"\n{config.TICKER_SYMBOL} Data Statistics Summary:")
    print(f"Price range: ${df_adjusted['price'].min():.2f} to ${df_adjusted['price'].max():.2f}")
    print(f"Daily returns range: {daily_returns.min():.2f}% to {daily_returns.max():.2f}%")
    print(f"Time range: {df_adjusted.index.min()} to {df_adjusted.index.max()}")

# Create visualization
visualize_price_data(df_adjusted, df_downsampled, daily_returns)

# Cell: Log-Transformed Visualization
def visualize_log_price_data(df_adjusted, df_downsampled, daily_returns):
    """Create comprehensive visualization plots with log-transformed data"""
    # Apply log transform to prices and returns
    log_prices = np.log(df_adjusted['price'] + config.LOG_EPSILON)
    log_downsampled = np.log(df_downsampled['price'] + config.LOG_EPSILON)
    log_returns = np.log(daily_returns + config.LOG_EPSILON)

    plt.figure(figsize=config.PLOT_FIGSIZE)

    # Plot 1: Log-transformed prices
    plt.subplot(4, 1, 1)
    plt.plot(df_downsampled.index, log_downsampled,
            color=plot_colors.TRAINING,
            label=f'{config.TICKER_SYMBOL} Log Price',
            alpha=config.PLOT_ALPHA)

    # Add split lines
    for (split_date, ratio), color in zip(config.SPLITS_INFO, plot_colors.SPLIT_LINES):
        split_datetime = pd.to_datetime(split_date)
        if split_datetime.tz is None:
            split_datetime = split_datetime.tz_localize('UTC')
        plt.axvline(x=split_datetime, color=color, linestyle='--',
                   label=f'Split ({ratio}:1)', alpha=config.PLOT_ALPHA)
    plt.title(plot_labels.LogTimeSeries.ADJUSTED)
    plt.xlabel(plot_labels.LogTimeSeries.X_LABEL)
    plt.ylabel(plot_labels.LogTimeSeries.Y_LABEL)
    plt.legend()
    plt.grid(True)

    # Plot 2: Log-transformed price distribution
    plt.subplot(4, 1, 2)
    plt.hist(log_downsampled,
            bins=config.HISTOGRAM_BINS,
            alpha=config.PLOT_ALPHA,
            color='red')
    plt.title(plot_labels.LogDistribution.ADJUSTED)
    plt.xlabel(plot_labels.LogDistribution.X_LABEL)
    plt.ylabel(plot_labels.LogDistribution.Y_LABEL)

    # Plot 3: Log-transformed returns distribution
    plt.subplot(4, 1, 3)
    plt.hist(log_returns,
            bins=config.HISTOGRAM_BINS,
            alpha=config.PLOT_ALPHA,
            color='red')
    plt.title(plot_labels.LogReturns.TITLE)
    plt.xlabel(plot_labels.LogReturns.X_LABEL)
    plt.ylabel(plot_labels.LogReturns.Y_LABEL)
    plt.grid(True)

    # Plot 4: Log-transformed volatility
    plt.subplot(4, 1, 4)
    vol_df = log_prices.to_frame('price')
    vol_df = vol_df.resample(config.VOLATILITY_RESAMPLE_FREQ).agg({'price': ['std']}).dropna()
    vol_df_plot = downsample_for_plotting(vol_df)

    plt.plot(vol_df_plot.index, vol_df_plot['price']['std'],
            color=plot_colors.VOLATILITY)

    # Add split lines to volatility plot
    for (split_date, ratio), color in zip(config.SPLITS_INFO, plot_colors.SPLIT_LINES):
        split_datetime = pd.to_datetime(split_date)
        if split_datetime.tz is None:
            split_datetime = split_datetime.tz_localize('UTC')
        plt.axvline(x=split_datetime, color=color, linestyle='--',
                   alpha=config.PLOT_ALPHA/2)
    plt.title(plot_labels.LogVolatility.TITLE)
    plt.xlabel(plot_labels.LogVolatility.X_LABEL)
    plt.ylabel(plot_labels.LogVolatility.Y_LABEL)
    plt.grid(True)

    plt.tight_layout()
    plt.show()

    # Print statistics summary
    print(f"\n{config.TICKER_SYMBOL} Log-Transformed Statistics Summary:")
    print(f"Log price range: {log_prices.min():.2f} to {log_prices.max():.2f}")
    print(f"Log returns range: {log_returns.min():.2f} to {log_returns.max():.2f}")
    print(f"Log volatility range: {vol_df['price']['std'].min():.2f} to {vol_df['price']['std'].max():.2f}")

# Create log-transformed visualization
visualize_log_price_data(df_adjusted, df_downsampled, daily_returns)

"""# Prepping data to be modified. Adding the columns: split adjusted price, and scaled price."""
