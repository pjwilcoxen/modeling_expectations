# Input files

Excel worksheets with expected values of the model's exogenous variables for each simulation. The names correspond to variables in the paper as follows:

* `a` = technology parameter alpha
* `td` = dividend tax Z
* `s` = production tax credit PTC
* `ITC` = investment tax credit ITC

Note that a number of simulations have identical exogenous variables. Those runs differ in the expectations mechanism used for endogenous variables, and many are part of a rolling simulation of a transition path baseline. See the [model.toml](../model.toml) file for more information.
