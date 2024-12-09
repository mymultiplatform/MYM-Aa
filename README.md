
# Ticker Data Analysis and Visualization

This repository contains a comprehensive data analysis pipeline for analyzing and visualizing stock ticker data. The primary focus is on **NVIDIA (NVDA)** stock, with features to adjust for stock splits, normalize data, and compute various statistics for financial analysis.

---

## Features

### 1. **Data Loading**
- Utilizes **GPU acceleration** for efficient data handling using `cuDF`.
- Processes multiple CSV files containing historical trading data.

### 2. **Stock Split Adjustment**
- Automatically adjusts historical price data for stock splits based on NVIDIA's split history.

### 3. **Data Transformation**
- Computes daily returns.
- Logarithmically transforms and scales data for better analysis.

### 4. **Statistical Analysis**
- Calculates key statistics like:
  - Mean, Median, Std Dev, Skewness, Kurtosis
  - Value at Risk (VaR)
  - Sharpe Ratio
  - Jarque-Bera test for normality.

### 5. **Data Visualization**
- Creates insightful plots:
  - Adjusted and unadjusted price time series.
  - Price distributions.
  - Daily returns distributions.
  - Hourly price volatility.
  - Log-transformed counterparts of the above.

### 6. **Data Normalization**
- Normalizes prices to a range of 0-1 with configurable buffer.
- Supports scaling log-transformed prices.

---

## Dependencies
- **Python Libraries**:
  - `yfinance`
  - `pandas`
  - `matplotlib`
  - `cuDF` (GPU acceleration)
  - `torch`
  - `seaborn`
  - `scikit-learn`
  - `numpy`
  - `scipy`

- **Google Colab** (optional):
  - Includes integration for Google Drive for seamless file handling.

---

## File Breakdown
- **Imports and Setup**: Handles dependencies and GPU checks.
- **Data Directory Config**: Defines file paths for training and testing data.
- **Stock Split Adjustment**: Adjusts price data for historical splits.
- **Visualization**: Generates multi-panel plots to interpret data trends and anomalies.
- **Statistical Analysis**: Computes metrics to understand return distributions and risks.

---

## Usage

### 1. **Set Up the Environment**
- Clone the repository and ensure all dependencies are installed.
- Optionally mount Google Drive for CSV file access.

### 2. **Customize Configuration**
- Modify settings in the `Config` class to analyze different tickers or date ranges.

### 3. **Run the Notebook**
- Execute the provided script to analyze and visualize stock ticker data.

### 4. **Analyze Results**
- Review output plots and statistical summaries for insights into the stock's historical performance.

---

## Sample Outputs
### Plots
- **Split-adjusted price time series with split markers**
- **Price distribution histograms**
- **Daily returns distribution**
- **Volatility over time**

### Statistical Summaries
- **Basic stats**: Mean, Median, Std Dev, etc.
- **Risk metrics**: VaR, Sharpe Ratio.
- **Normality test**: Jarque-Bera results.

---

## Future Enhancements
- Add support for multiple tickers.
- Extend analysis to include more financial metrics (e.g., Moving Averages, RSI).
- Improve visualizations with interactive tools (e.g., Plotly).

---

### License
This project is open-source and available under the [MIT License](LICENSE).


# MYM-Aa


**QAlgo Trade**
