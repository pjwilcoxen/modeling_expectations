# Modeling Expectations

The files in this repository provide the code, input files, and results for the example numerical model discussed in "Modeling Expectations in General Equilibrium".

## Key files

Here are the key scripts and the model's configuration file. The remaining files in the main directory are logs.

1. `model.py`: Python code for the model. It is run via `python model.py`.

1. `model.toml`: The model's configuration file. Has brief internal documentation describing the settings.

1. `plot-basic.py`: Plots results for exogenous or endogenous price runs depending on the `endog_p` setting in `model.toml`.

1. `plot-compare.py`: Draws comparison plots showing exogenous and endogenous price results for each run.

## Subdirectories

There are four subdirectories.

1. `1-in`: Contains an Excel input file for each run.

1. `2-out-ex`: Contains a CSV file of results for each exogenous-price run as well as a number of figures.

1. `3-out-en`: Contains results for each endogenous-price run as well as a number of figures.

1. `4-out-cmp`: Contains figures comparing exogenous and endogenous price runs.
