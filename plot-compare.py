"""
plot-compare.py
Aug 2025 PJW

Comparison plots from investment experiments.
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
#  get_files(odir)
#
#  Get the list of CSV files in the output directory.
#=======================================================================

def get_files(odir):
    files = os.listdir(odir)
    files = [f for f in files if f.endswith('.csv')]
    return files

#=======================================================================
#  get_data(odir,files)
#
#  Read the data from the specified files in the output directory.
#=======================================================================

def get_data(odir,files):

    data = { os.path.splitext(f)[0]: pd.read_csv(f'{odir}/{f}') for f in files }

    data = pd.concat(data)
    data = data.reset_index(0)
    data = data.rename(columns={'level_0':'run'})

    data['legend'] = data['run'].replace(legend_mapping)
    data = data.query("legend != 'omit'")
    data = data.sort_values(['legend','period'])
    data = data.reset_index(drop=True)

    return data

#=======================================================================
#  drawplot(include,title,grp,run)
#
#  Draw the plot for the specified group and run.
#=======================================================================

def drawplot(include,title,grp,run):

    ql.log('Figure',title)

    #
    #  Print some summary information
    #

    ss = stack[ stack['legend'].str[0].isin(include) ]
    ss = ss.query('period == 0 or period == 100')
    ss = ss[['period','legend','lam','inv','cap','Closure']]
    ss = ss.set_index(['legend','Closure','period']).unstack().round(2)
    ql.log('Summary',ss)

    #
    #  Trim the data to the specified runs and rename the legend
    #

    trim = short[ legkey.isin(include) ].copy()
    trim = trim.rename(columns={'legend':'Experiment'})

    #
    #  Tweak the B legend for clarity
    #

    is_b = trim['Experiment'].str[0] == 'B'

    if any(is_b):
        trim.loc[is_b,'Experiment'] = "B: ITC, permanent"

    #
    #  Draw the plots
    #

    fig,(axL,axR) = plt.subplots(1,2,figsize=(8,4))

    if show_titles:
        fig.suptitle(title)

    sns.lineplot(data=trim,x='period',y='inv',
                 hue='Experiment',style='Closure',ax=axL,legend=False)

    axL.set_title('Investment')
    axL.set_xlabel('Period')
    axL.set_ylabel('Percent Change from Initial Period')

    sns.lineplot(data=trim,x='period',y='cap',
                 hue='Experiment',style='Closure',ax=axR)

    axR.set_title('Capital Stock')
    axR.set_xlabel('Period')
    axR.set_ylabel('')#'Percent of Baseline')
    axR.legend(loc='upper left',bbox_to_anchor=(1,1))

    fig.tight_layout()

    figname = f'{odir3}/fig{grp}-cmp-A{run}.png'
    fig.savefig(figname)
    ql.log('Wrote image',figname)

    #
    #  Make a dataframe for plotting expected vs actual prices
    #

    pcomp = trim[['period','Experiment','Closure','p','p_market']]

    pcomp = pcomp.melt(
        id_vars=['period','Experiment','Closure'],
        var_name='Type',
        value_name='Price'
        )

    pmap ={ 'p':'Expected', 'p_market':'Actual' }
    pcomp['Type'] = pcomp['Type'].replace(pmap)

    is_en = pcomp['Closure'] == 'P end'

    #
    #  Fix labeling of Q for clarity
    #

    is_q = pcomp['Experiment'].str[0] == 'Q'

    if any(is_q & is_en):
        pcomp.loc[is_q,'Experiment'] += ", PF"

    #
    #  Draw the plot
    #

    fig,axR = plt.subplots()

    if show_titles:
        fig.suptitle(title)

    sns.lineplot(data=pcomp[is_en],x='period',y='Price',
                 hue='Experiment',style='Type',ax=axR)

    axR.set_title('Price Trajectories')
    axR.set_xlabel('Period')
    axR.set_ylabel('')#'Percent of Baseline')
    axR.legend(loc='upper left',bbox_to_anchor=(1,1))

    fig.tight_layout()

    figname = f'{odir3}/fig{grp}-cmp-A{run}-P.png'
    fig.savefig(figname)
    ql.log('Wrote image',figname)

#=======================================================================
#  Main program
#=======================================================================

#
#  Read configuration information
#

with open("model.toml", "rb") as f:
    info = tomllib.load(f)

    odir1 = info['out_ex']
    odir2 = info['out_en']
    odir3 = info['out_cm']

    legend_mapping = info['legend']
    last_yr = info['last_year']
    show_titles = info['show_titles']
    roll = info['roll']

#
#  Start logging
#

ql = logger('plot-compare.log')

ql.log('Run legends',legend_mapping)
ql.log('Last year',last_yr)
ql.log('Show titles',show_titles)
ql.log('Roll',roll)

#
#  Read the results
#

files1 = get_files(odir1)
files2 = get_files(odir2)

#
#  Find runs that are in both directories
#

files = set(files1).intersection(files2)

ql.log('Overlapping run files found',files)

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

data = {
    'P ex': get_data(odir1,files),
    'P end': get_data(odir2,files)
    }

stack = pd.concat(data)
stack = stack.reset_index(0)
stack = stack.rename(columns={'level_0':'Closure'})

#
#  Standardize variables for plotting
#

norm =  stack.query('run=="r01-baseline" and period==0').iloc[0]

normed = stack.copy()
for k in ['inv','cap','p','q','p_market']:
    normed[k] = 100*normed[k]/norm[k] - 100

short = normed.query(f'period <= {last_yr}').copy()

legkey = short['legend'].str[0]

#========================================================================
#  Draw the plots
#========================================================================

#
#  Group 1
#

fn = 1
for k in ['B','C','D']:

    include = ['A',k]
    title = 'Immediate Permanent Policies with Repeal Risk'

    drawplot(include,title,fn,k)

#
#  Group 2
#

fn += 1
for k in ['G','H','I','J']:

    include = ['A',k]
    title = 'Delayed Permanent Policies with Varying Credibility'

    drawplot(include,title,fn,k)

#
#  Group 3
#

fn += 1
for k in ['E','F','K','L']:

    include = ['A',k]
    title = 'Temporary Policies with Continuation Risk'

    drawplot(include,title,fn,k)

#
#  Group 4
#

fn += 1
for k in ['M','N','P']:

    include = ['A',k]
    title = 'Delayed Technology Decline'

    drawplot(include,title,fn,k)

#
#  Group 5
#

fn += 1
for k in ['Q']:

    include = ['A',k]
    title = 'Alternative Baselines'

    drawplot(include,title,fn,k)

#
#  Group 6
#

fn += 1
for k in ['R']:

    include = ['Q',k]
    title = 'Alternative Baselines'

    drawplot(include,title,fn,k)

#
#  All done
#

ql.close()
