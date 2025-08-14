"""
plot-basic.py
Jul 2025 PJW

Plot results from investment experiments.
"""

import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import tomllib
from quicklog import logger
import sys

plt.rcParams['figure.dpi'] = 300

#=======================================================================
#  drawplot(include,title,var1,var2,grp,closure)
#
#  Drawing the plots
#=======================================================================

def drawplot(include: list, title: str, var1: str, var2: str,
             grp:int, closure:str ) -> plt.Figure:
    """ Draw a plot for the specified variables.

    Parameters
    ----------
    include : list
        List of run legends to include in the plot.
    title : str
        Title for the plot.
    var1 : str
        First variable to plot on the left axis.
    var2 : str
        Second variable to plot on the right axis.
    grp : int
        Group number for the plot.
    closure : str
        Closure type, either 'en' or 'ex' for price closure.
    """

    #
    #  Define axis titles for variables to plot
    #

    axis_titles = {
        'inv':'Investment',
        'cap':'Capital Stock',
        'p':'Price',
        'q':'Quantity',
        }

    #
    #  Check that the variables are in the axis titles
    #

    assert var1 in axis_titles and var2 in axis_titles

    ql.log(f'Group {grp} Figure',title)

    #
    #  Print a short summary of key data
    #

    ss = normed[ normed['legend'].str[0].isin(include) ]
    ss = ss.query('period == 0 or period == 100')
    ss = ss[['period','legend','lam','inv','cap']]
    ss = ss.set_index(['legend','period']).unstack().round(2)
    ql.log('Summary',ss)

    #
    #  Trim the data down to the desired runs
    #

    trim = short[ legkey.isin(include) ]

    #
    #  Draw the plot
    #

    fig,(axL,axR) = plt.subplots(1,2,figsize=(8,4))

    if show_titles:
        fig.suptitle(title)

    sns.lineplot(data=trim,x='period',y=var1,
                 hue='legend',style='legend',ax=axL,legend=False)

    axL.set_title(axis_titles[var1])
    axL.set_xlabel('Period')
    axL.set_ylabel('Percent Change from Initial Period')

    sns.lineplot(data=trim,x='period',y=var2,
                 hue='legend',style='legend',ax=axR)

    axR.set_title(axis_titles[var2])
    axR.set_xlabel('Period')
    axR.set_ylabel('')#'Percent of Baseline')
    axR.legend(loc='upper left',bbox_to_anchor=(1,1))

    fig.tight_layout()

    if var1 == 'inv' and var2 == 'cap':
        fname = f'{odir}/fig{grp}b-{closure}-IK.png'
    else:
        fname = f'{odir}/fig{grp}a-{closure}-PQ.png'

    fig.savefig(fname)

    return fig

#=======================================================================
#  Main program
#=======================================================================

#
#  Read configuration information
#

with open("model.toml", "rb") as f:
    info = tomllib.load(f)

    od_ex = info['out_ex']
    od_en = info['out_en']

    endog_p = info['endog_p']

    legend_mapping = info['legend']
    last_yr = info['last_year']
    show_titles = info['show_titles']
    roll = info['roll']

odir = od_en if endog_p else od_ex
closure = 'en' if endog_p else 'ex'

#
#  Tweak the A and Q legends when price is endogenous to resolve ambiguity
#

for f,l in legend_mapping.items():
    if (l[0] == 'Q' or l[0] == 'A') and endog_p:
        legend_mapping[f] = l+', PF'

#
#  Start logging
#

ql = logger(f'plot-basic-{closure}.log')

ql.log('Endogenous price',endog_p)
ql.log('Run legends',legend_mapping)
ql.log('Last year',last_yr)
ql.log('Show titles',show_titles)
ql.log('Roll',roll)

#
#  Read the results files
#

files = os.listdir(odir)
files = [f for f in files if f.endswith('.csv')]

ql.log('Run files found',files)

#
#  Check that all files have a legend mapping
#

for f in files:
    stem = os.path.splitext(f)[0]
    if stem not in legend_mapping:
        print('No mapping for run:',stem)
        sys.exit()

#
#  Read the data files into a single DataFrame
#

data = { os.path.splitext(f)[0]: pd.read_csv(f'{odir}/{f}') for f in files }
data = pd.concat(data)
data = data.reset_index(0)
data = data.rename(columns={'level_0':'run'})

#
#  Add legends
#

data['legend'] = data['run'].replace(legend_mapping)
data = data.query("legend != 'omit'")
data = data.sort_values(['legend','period'])
data = data.reset_index(drop=True)

#
#  Standardize results for plotting
#

norm =  data.query('run=="r01-baseline" and period==0').iloc[0]

normed = data.copy()
for k in ['inv','cap','p','q']:
    normed[k] = 100*normed[k]/norm[k] - 100

short = normed.query(f'period <= {last_yr}').copy()

run = short['run']
legkey = short['legend'].str[0]

#=======================================================================
#  Draw the plots
#=======================================================================

#
#  Group 1
#

fn = 1
include = ['A','B','C','D']
title = 'Immediate Permanent Policies with Repeal Risk'

fig = drawplot(include,title,'inv','cap',fn,closure)
if endog_p:
    fig = drawplot(include,title,'q','p',fn,closure)

#
#  Group 2
#

fn += 1
include = ['G','H','I','J']
title = 'Delayed Permanent Policies with Varying Credibility'

fig = drawplot(include,title,'inv','cap',fn,closure)
if endog_p:
    fig = drawplot(include,title,'q','p',fn,closure)

#
#  Group 3
#

fn += 1
include = ['E','F','K','L']
title = 'Temporary Policies with Continuation Risk'

fig = drawplot(include,title,'inv','cap',fn,closure)
if endog_p:
    fig = drawplot(include,title,'q','p',fn,closure)

#
#  Group 4
#

fn += 1
include = ['A','M','N','P']
title = 'Delayed Technology Decline'

fig = drawplot(include,title,'inv','cap',fn,closure)
if endog_p:
    fig = drawplot(include,title,'q','p',fn,closure)

#
#  Alternative baselines
#

fn += 1
include = ['A','Q']
title = 'Alternative Baselines'

fig = drawplot(include,title,'inv','cap',fn,closure)
if endog_p:
    fig = drawplot(include,title,'q','p',fn,closure)

#
#  Alternative baselines, including inertial prices
#

if endog_p:

    fn += 1
    include = ['A','Q','R']
    title = 'Alternative Baselines'

    fig = drawplot(include,title,'inv','cap',fn,closure)
    fig = drawplot(include,title,'q','p',fn,closure)

    fn += 1
    include = ['A','Q','R','T']
    title = 'Alternative Baselines'

    fig = drawplot(include,title,'inv','cap',fn,closure)
    fig = drawplot(include,title,'q','p',fn,closure)

    fn += 1
    include = ['A','Q','R','U','V','W','X','Y','Z']
    title = 'Alternative Baselines'

    fig = drawplot(include,title,'inv','cap',fn,closure)
    fig = drawplot(include,title,'q','p',fn,closure)

#
#  Temporary policies, including inertial prices
#

fn += 1
include = ['E','S']
title = 'Temporary Policies with Continuation Risk'

fig = drawplot(include,title,'inv','cap',fn,closure)
if endog_p:
    fig = drawplot(include,title,'q','p',fn,closure)

#
#  All done
#

ql.close()
