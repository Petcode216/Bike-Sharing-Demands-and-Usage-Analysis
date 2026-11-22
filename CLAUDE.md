# Project 02 — Bike Sharing Demand & Usage Pattern Analysis

## 1. Project Overview

This project analyzes the Bike Sharing Dataset, a historical bike-rental dataset commonly distributed through the UCI Machine Learning Repository. The standard dataset contains rental records from the Capital Bikeshare system in Washington, D.C., covering 2011–2012.

The project simulates a real-world Data Analyst assignment: investigating bike-sharing demand, usage patterns, temporal trends, weather-related differences, and customer segments to identify opportunities for improving bike availability and operational planning.

The analysis should follow a structured, evidence-based approach, starting with business understanding and data exploration, followed by data cleaning, analysis, visualization, and actionable recommendations.

Inspect the locally installed files and accompanying documentation before assuming the exact dataset version, filenames, columns, or coverage.

## 2. Business Context

A bike-sharing service allows customers to rent bicycles from a network of stations or designated rental locations. The operator needs to understand when and under what conditions bikes are most frequently rented.

Demand can vary by hour, weekday, season, weather, and customer type. Understanding these patterns can help the operator plan bicycle availability, maintenance, staffing, and service capacity.

The primary business question is:

**What factors and usage patterns are associated with bike rental demand, and how can the operator use these insights to improve service availability and operational planning?**

The analysis should investigate relationships between rental volume, time-related variables, weather conditions, seasonal patterns, and user types where these fields are available.

Do not assume that weather, temperature, or calendar effects directly cause changes in demand. Investigate relationships using appropriate analytical methods and distinguish correlation from causation.

## 3. Analytical Objectives

Organize the analysis around four major business areas.

### 3.1 Rental Demand & Temporal Patterns

Investigate:

- Overall distribution of bike rental counts.
- Rental demand by hour of day, if hourly records are available.
- Rental demand by day of week.
- Differences between weekdays and weekends.
- Monthly and yearly demand trends.
- Seasonal differences in rental activity.
- Peak and low-demand periods.
- Differences between working days, weekends, and holidays where supported by the dataset.

Potential KPIs:

- Total rentals.
- Average rentals per observation period.
- Median rentals per observation period.
- Maximum and minimum rental counts.
- Average rentals by hour.
- Average rentals by weekday.
- Peak-demand hour and day.
- Month-over-month or year-over-year change, where the time coverage supports it.

Be explicit about the observation period represented by each metric. Daily and hourly rental counts must not be compared as if they represented the same time interval.

### 3.2 Weather & Environmental Conditions

Investigate:

- Rental demand across weather conditions.
- Relationship between temperature and rental counts.
- Relationship between perceived temperature and rental counts.
- Relationship between humidity and rental counts.
- Relationship between wind speed and rental counts.
- Demand differences across seasons.
- Demand differences across weather categories.
- Whether weather-related patterns differ by hour, weekday, or user type.

Potential KPIs:

- Average rentals by weather category.
- Average rentals by temperature range.
- Average rentals by season.
- Rental-count differences across weather groups.
- Correlation between weather variables and rental counts.

Consult the dataset documentation before interpreting normalized or encoded weather variables. Do not assume that a numerical weather code is a continuous measurement.

### 3.3 User Segment Performance

Investigate:

- Differences between casual and registered users, where these columns exist.
- Share of total rentals contributed by each user type.
- Casual versus registered demand by hour.
- Casual versus registered demand by weekday and weekend.
- Seasonal differences between user types.
- Differences in weather sensitivity between user types.
- Time periods in which each user segment contributes most to demand.

Potential KPIs:

- Total casual rentals.
- Total registered rentals.
- Casual rental share.
- Registered rental share.
- Average rentals by user type and time period.
- Casual-to-registered rental ratio.

Do not treat rental counts as unique customer counts. The dataset may record rental events or aggregated rentals rather than individual customer identities.

### 3.4 Operational & Capacity Planning

Investigate:

- Periods with consistently high rental demand.
- Periods with consistently low rental demand.
- Differences in demand across hours, weekdays, and seasons.
- Potential demand patterns relevant to bicycle availability and maintenance planning.
- Whether demand peaks differ between casual and registered users.
- Whether weather conditions are associated with unusually low or high demand.

Potential operational considerations:

- Time periods that may require greater bicycle availability.
- Periods suitable for routine maintenance.
- Seasonal changes that may affect operational planning.
- Demand patterns that could inform staffing and resource allocation.

The dataset may not contain station-level inventory, trip routes, bicycle availability, or maintenance records. Do not claim to measure stockouts, station imbalance, fleet utilization, or unmet demand unless the necessary data is actually available. Present operational recommendations as implications of observed rental patterns, not as directly measured outcomes.

## 4. Dataset Information

Primary dataset:

Bike Sharing Dataset.

Common source:

UCI Machine Learning Repository — Bike Sharing Dataset.

Source:

https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset

The commonly distributed dataset includes two CSV files:

| Dataset | Description |
|---|---|
| day.csv | Daily bike rental counts and associated calendar/weather information |
| hour.csv | Hourly bike rental counts and associated calendar/weather information |
| Readme.txt | Dataset description, variable definitions, and relevant documentation |

Check the actual local project files. The dataset may have been downloaded, extracted, renamed, or packaged differently.

### Important Variables

The standard dataset commonly contains the following fields. Verify the local schema and documentation before using them.

| Variable | Description |
|---|---|
| instant | Record index |
| dteday | Date |
| season | Season category |
| yr | Year indicator |
| mnth | Month |
| hr | Hour; available in hourly data |
| holiday | Holiday indicator |
| weekday | Day-of-week indicator |
| workingday | Working-day indicator |
| weathersit | Weather situation category |
| temp | Normalized temperature |
| atemp | Normalized feeling temperature |
| hum | Normalized humidity |
| windspeed | Normalized wind speed |
| casual | Count of casual-user rentals |
| registered | Count of registered-user rentals |
| cnt | Total bike rental count |

Important considerations:

- The daily and hourly files represent different observation granularities.
- The standard `cnt` field represents the total rental count for an observation.
- In the standard dataset, `casual` and `registered` are components of `cnt`; validate this relationship locally.
- `instant` is a record index, not a meaningful measure of demand.
- The standard weather and environmental variables are normalized or encoded. Consult the data dictionary before interpreting their values.
- The `hr` field is present in hourly data, not daily data.
- Calendar fields such as `yr`, `mnth`, `weekday`, and `workingday` may overlap with information derived from `dteday`.

### Important Data Relationships & Granularity

Understand the observation unit before performing analysis.

For the standard dataset:

- One row in `day.csv` represents one day.
- One row in `hour.csv` represents one hour.
- The hourly dataset contains multiple observations for a date.
- Daily rental counts aggregate activity across a day.
- Hourly rental counts describe activity within an individual hour.

Important considerations:

- Do not append daily and hourly records into one table as if they had the same grain.
- Do not sum daily and hourly counts together; that would double-count rental activity.
- Use the hourly dataset for intraday demand analysis.
- Use the daily dataset for daily-level and longer-term trend analysis.
- If both files are used, compare them only after aligning their observation periods and aggregation levels.
- Validate that `cnt` equals `casual + registered` where these fields are available.
- Check date coverage, missing time periods, and duplicate records before calculating trends.

Always identify the intended analytical grain before aggregating, comparing, or joining datasets.

## 5. Analytical Workflow

Follow this sequence unless there is a documented reason to change it.

### Phase 1 — Business Understanding

- Understand the bike-sharing business problem.
- Define analytical objectives.
- Identify the available dataset files.
- Read the dataset documentation and data dictionary.
- Determine whether the analysis will use daily data, hourly data, or both.
- Understand the observation grain and variable definitions.
- Define initial KPIs and business questions.

### Phase 2 — Data Exploration

- Inspect dataset dimensions and column names.
- Examine data types.
- Identify missing values.
- Identify duplicate records.
- Examine categorical distributions.
- Investigate numerical distributions and outliers.
- Check date and time ranges.
- Validate category codes and value ranges against the documentation.
- Compare `cnt` with `casual + registered` where applicable.
- Document initial observations and potential data-quality issues.

### Phase 3 — Data Cleaning and Preparation

- Handle missing values according to their meaning and analytical relevance.
- Investigate duplicates before removing them.
- Validate data types and date formats.
- Identify invalid or inconsistent records.
- Verify encoded categorical variables against the data dictionary.
- Interpret normalized weather variables correctly.
- Create analytical features such as hour, weekday, month, or season only when useful and not already represented.
- Preserve original columns wherever possible.
- Avoid unnecessary transformations of already-clean data.
- Document every significant transformation.

### Phase 4 — Exploratory Data Analysis

- Analyze daily and hourly demand at their appropriate granularities.
- Investigate demand distributions and temporal trends.
- Compare demand by hour, weekday, month, and season.
- Compare working days, weekends, and holidays.
- Examine relationships between weather variables and rentals.
- Compare casual and registered users where available.
- Investigate interactions between time, weather, and user type.
- Use appropriate visualizations.
- Validate findings using the underlying data.

### Phase 5 — Statistical Analysis

Where appropriate, apply:

- Descriptive statistics.
- Correlation analysis.
- Group comparisons.
- Hypothesis testing.
- Confidence intervals.
- Analysis of variance or suitable non-parametric alternatives.
- Regression analysis when the research question supports it.

Potential questions include:

- Is average rental demand different between working days and non-working days?
- Does rental demand differ across seasons?
- Are rental counts associated with temperature or humidity?
- Do casual and registered users exhibit different hourly demand patterns?
- Are observed differences large enough to be practically meaningful?

Explain why a statistical method is appropriate before applying it.

Check assumptions, sample sizes, distribution characteristics, and dependence between observations. Account for repeated observations over time where relevant. Do not treat statistical significance as proof of business importance or causation.

### Phase 6 — Business Insights

Translate analytical findings into business language.

Each major insight should explain:

1. What happened?
2. What evidence supports the finding?
3. Which time periods or user segments are involved?
4. Why might it matter to the business?
5. What action could the operator consider?

Separate confirmed findings from hypotheses and possible explanations.

Recommendations about fleet allocation, staffing, or maintenance should be clearly framed as operational implications unless inventory, staffing, or maintenance data is available to validate them directly.

### Phase 7 — Reporting

Produce:

- A well-structured project README.
- Clear and appropriately labeled visualizations.
- A summary of important findings.
- Evidence-based operational recommendations.
- Analytical limitations and assumptions.
- Reproducible code and documented data preparation steps.

## 6. Technical Standards

### Language and Libraries

Use Python as the primary programming language.

Preferred libraries:

- pandas: data manipulation.
- NumPy: numerical operations.
- Matplotlib: visualization.
- Seaborn: statistical visualization.
- SciPy: statistical analysis.
- Statsmodels: statistical modeling and inference when appropriate.
- scikit-learn: machine learning when a predictive task is explicitly in scope.
- Plotly: interactive visualization when useful.
- SQL: relational data exploration and analytical queries when appropriate.

Use additional libraries only when they provide meaningful value.

### Code Quality

- Write readable, modular, maintainable code.
- Use meaningful variable and function names.
- Avoid unnecessary code duplication.
- Separate data loading, cleaning, analysis, and visualization logic.
- Use functions for reusable transformations.
- Include comments where logic is not immediately obvious.
- Avoid unnecessarily complicated abstractions.
- Prefer clear and understandable solutions over clever implementations.
- Use project-relative paths rather than machine-specific absolute paths.
- Follow the existing environment and dependency-management setup.

### Notebook Standards

Organize notebooks in a logical sequence.

Each notebook should include:

- A clear title.
- Its analytical objective.
- Relevant business context.
- Dataset and observation-grain description.
- Code and outputs.
- Explanations of important observations.
- Conclusions and limitations.

Notebooks should tell an analytical story rather than function as collections of disconnected code cells.

Suggested notebook sequence, to be adapted to the existing project:

1. Business Understanding & Data Overview
2. Data Quality Assessment & Preparation
3. Rental Demand & Temporal Analysis
4. Weather & Environmental Analysis
5. User Segment Analysis
6. Statistical Analysis & Business Insights

Do not create every notebook automatically. Create only the notebooks that fit the project scope and available data.

## 7. Data Management Rules

Follow this directory structure where practical. Preserve the existing project structure if it is already established.

```text
Bike Sharing/
│
├── CLAUDE.md
├── README.md
├── requirements.txt
│
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── notebooks/
│
├── src/
│   ├── data/
│   ├── analysis/
│   └── visualization/
│
└── reports/
    ├── figures/
    └── findings/
```

Rules:

- Never modify original files inside `data/raw/`.
- Save temporary transformations in `data/interim/`.
- Save validated analytical datasets in `data/processed/`.
- Store reusable Python code inside `src/`.
- Store notebooks inside `notebooks/`.
- Save final charts inside `reports/figures/`.
- Save written findings inside `reports/findings/`.
- Do not commit large raw datasets to Git unless explicitly requested.
- Do not expose private credentials, tokens, or sensitive information.
- Do not create duplicate copies of the same dataset without a clear reason.

## 8. Analytical Integrity

These rules are mandatory.

- Never fabricate statistics, findings, or business metrics.
- Never invent missing dataset values.
- Never assume a relationship exists without examining the data.
- Validate important calculations before presenting conclusions.
- Check row counts before and after data transformations.
- Do not mix daily and hourly observations in the same analysis without a valid aggregation strategy.
- Do not double-count rentals by combining daily and hourly totals.
- Verify category codes and normalized variables using the documentation.
- Document assumptions and limitations.
- Clearly distinguish correlation from causation.
- Do not claim to measure bike availability, stockouts, station imbalance, or unmet demand without the required operational data.
- Do not hide inconvenient findings.
- Do not present unreliable results as definitive conclusions.

When information is insufficient, explicitly state what is missing and what additional investigation is needed.

## 9. Working Guidelines for Claude Code

Before modifying any files:

1. Inspect the existing project structure.
2. Read this CLAUDE.md.
3. Identify the actual dataset files and read their documentation.
4. Inspect the relevant columns, data types, and observation grain.
5. Understand the task's scope.
6. Explain the proposed approach when the task involves significant changes.

While working:

- Work incrementally.
- Focus only on the requested project or task.
- Do not modify unrelated files.
- Do not overwrite existing work without checking its contents.
- Avoid unnecessary dependencies.
- Explain important analytical decisions.
- Validate code and outputs when possible.
- Do not assume that the local dataset matches the standard UCI distribution exactly.
- Ask a focused question if the dataset version or business objective materially changes the correct approach.

After completing a task, report:

- What was changed or created.
- Why the change was necessary.
- Important assumptions.
- Validation performed.
- Any remaining issues or limitations.

Do not claim that code or analysis has been validated unless it has actually been executed and checked.

## 10. Definition of Success

The completed project should demonstrate that the analyst can:

- Understand a real-world business problem.
- Inspect and understand a structured dataset.
- Assess data quality and prepare data appropriately.
- Analyze time-based and categorical data.
- Manipulate and analyze data using Python and SQL.
- Conduct meaningful exploratory data analysis.
- Apply appropriate statistical methods.
- Build clear and informative visualizations.
- Identify demand patterns and differences between user segments.
- Extract evidence-based operational insights.
- Communicate practical recommendations.
- Produce clean, reproducible, well-documented work.

**The ultimate objective is to demonstrate business-oriented analytical thinking, not merely technical proficiency.**
