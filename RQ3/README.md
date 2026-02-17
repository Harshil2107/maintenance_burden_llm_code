# PR Churn Analysis

This repository contains scripts and analysis tools to compare the stability and churn of AI-generated code versus human-written code in pull requests.

## Project Structure

- `analyze_rq3.py`: Script to analyze conditional churn intensity (RQ3).
- `plot_churn_results.py`: Generates visualizations for churn metrics.
- `churn_analysis.py`: Core logic for calculating churn metrics.
- `analyze_prs.py`: Main script to process pull requests and extract metrics.
- `line_churn_analysis.py`: Detailed analysis of line-level churn.

## Setup

1.  Clone the repository.
2.  Ensure you have Python 3.x installed.
3.  Install dependencies:
    ```bash
    pip install pandas seaborn matplotlib
    ```

## Usage

### Running Analysis

To run the main analysis:
```bash
python analyze_rq3.py
```

### Generating Plots

To generate visualization plots:
```bash
python plot_churn_results.py
```

## Data

The analysis relies on CSV data files generated from repository scans:
- `pr_level_metrics.csv`
- `pr_level_metrics_250st.csv`
- `pr_level_metrics_500st.csv`

## Results

Results and plots are saved in the `plots/` directory or as specified in the scripts.
