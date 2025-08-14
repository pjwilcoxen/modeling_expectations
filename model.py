"""
model.py

Run simulations of the example model in "Modeling Expectations in
General Equilibrium".

Configuration information is read from model.toml and simulation definitions
are read from spreadsheets in the input directory. Results are written to
output directories that depend on whether the price is endogenous or exogenous.

The output files are CSV files with the same stem as the input files.
"""

import pandas as pd
import tomllib
import os
import numpy as np
import scipy.optimize as opt
from quicklog import logger

#=======================================================================
#  evaluate(p, exo, pars)
#
#  Evaluate the model for a given guess of the full price trajectory.
#=======================================================================

def evaluate(p: pd.Series, exo: pd.DataFrame, pars: dict) -> pd.DataFrame:
    """
    Evaluate the model for a given guess of prices.

    Parameters
    ----------
    p : pd.Series
        A series of prices indexed by period.
    exo : pd.DataFrame
        A dataframe of exogenous variables indexed by period.
    pars : dict
        A dictionary of parameters.

    Returns
    -------
    pd.DataFrame
        A dataframe of results including endogenous variables like
        capital stock, investment, output, and revenue.

    Notes
    -----
    This function calculates the steady state values, iterates backwards
    to find the shadow price of capital (lambda), and then iterates forward
    to find the capital stock in each period. It also calculates output,
    investment, and revenue from tax credits. The final price is adjusted
    based on demand elasticity to find the market price.
    """

    global n_it
    n_it += 1

    #  Get parameters from the pars dictionary

    r     = pars['r']
    delta = pars['delta']
    w     = pars['w']
    pk    = pars['pk']
    cap0  = pars['cap0']
    elast = pars['elast']
    scale = pars['scale']

    #  Log the starting and ending prices unless they are the same

    p1 = p.iloc[0]
    pN = p.iloc[-1]

    if p1 != pN:
        ql.log(f'Guess {n_it}',f'{p1} to {pN}')

    #  Crash if there are any missing values

    assert any(p.isna()) == False

    #  Start building a dataframe of results. Include all of the exogenous
    #  variables.

    d = exo.copy()

    #  Add the price guess

    d['p'] = p

    #  Evaluate some purely intra-temporal results

    d['p_net'] = p*(1+d['sub'])
    d['pk_net'] = pk*(1-d['itc'])

    d['gamma'] = (d['p_net']**2 * d['a']**2)/(4*w)

    #  Calculate the steady state values

    d['lam_ss'] = d['gamma']*(1-d['td'])/(r+delta)
    d['inv_ss'] = (d['gamma']/(r+delta) - d['pk_net'])/(2*w)
    d['cap_ss'] = d['inv_ss']/delta

    #  Set up information for backward iteration

    years = sorted(d.index)
    first_yr = min(years)
    last_yr = max(years)

    d['lam'] = None
    d['cap'] = None

    #  Impose the boundary conditions

    d.at[last_yr ,'lam'] = d.at[last_yr,'lam_ss']
    d.at[first_yr,'cap'] = cap0

    #  Walk backwards from period N-1 to 0 calculating lambda

    rev_years = sorted(years[:-1],reverse=True)

    for y in rev_years:
        next_lam = d.at[y+1,'lam']
        this_lam = (next_lam + d.at[y,'gamma']*(1-d.at[y,'td']))/(1+r+delta)
        d.at[y,'lam'] = this_lam

    #  Calculate investment in all periods given lambda

    d['inv'] = (d['lam']/(1-d['td'])-d['pk_net'])/(2*w)

    #  Walk forward from period 0 to N-1 calculating the capital stock

    for y in years[:-1]:
        this_cap = d.at[y,'cap']
        this_inv = d.at[y,'inv']
        next_cap = this_inv + (1-delta)*this_cap
        d.at[y+1,'cap'] = next_cap

    #  Calculate output and the revenue spent on tax credits

    d['q'] = d['p_net'] * d['a']**2 * d['cap']/(2*w)

    d['rev_ptc'] = d['sub']*p*d['q']
    d['rev_itc'] = d['itc']*pk*d['inv']

    #  Use demand elasticity to calculate p_market

    d['p_market'] = (d['q']/scale)**(1/elast)
    d['p_diff'] = d['p_market'] - p

    #  Return the result

    return d

#=======================================================================
#  miss_all(p_guess, exo, pars)
#
#  Calculate miss distances for all periods
#=======================================================================

def miss_all(p_guess: np.ndarray, exo, pars) -> np.ndarray:
    """
    Calculate the miss distances for a given guess of the price.

    This function takes a guess of the price trajectory and evaluates
    the model to find the difference between the market price and the
    guessed price for all periods.

    Parameters
    ----------
    p_guess : np.ndarray
        An array of guessed prices for each period.
    exo : pd.DataFrame
        A dataframe of exogenous variables indexed by period.
    pars : dict
        A dictionary of parameters.

    Returns
    -------
    np.ndarray
        An array of miss distances for each period, which is the difference
        between the market price and the guessed price.

    Notes
    -----
    This function uses the evaluate function to compute the model results
    for the guessed prices and then extracts the 'p_diff' column, which
    represents the difference between the market price and the guessed price.
    """

    p = pd.Series(p_guess)
    res = evaluate(p, exo, pars)

    return res['p_diff']

#=======================================================================
#  miss_one(p_guess, exo, pars)
#
#  Calculate a single miss distance for just period 0
#=======================================================================

def miss_one(p_guess, exo, pars) -> np.ndarray:
    """
    Calculate the miss distances for a given guess of the price.

    This function evaluates the model for a single period (period 0)
    and returns the miss distance, which is the difference between the
    market price and the guessed price for that period.

    Parameters
    ----------
    p_guess : np.ndarray
        An array of guessed prices for period 0.
    exo : pd.DataFrame
        A dataframe of exogenous variables indexed by period.
    pars : dict
        A dictionary of parameters.

    Returns
    -------
    np.ndarray
        A single value representing the miss distance for period 0,
        which is the difference between the market price and the guessed price.

    Notes
    -----
    This function is used when the model is solved with an inertial approach,
    where only the first period's price is adjusted based on the guess.
    """

    p = pd.Series(index=exo.index,data=p_guess[0])
    res = evaluate(p, exo, pars)

    return res.at[0,'p_diff']

#=======================================================================
#  Main program
#=======================================================================

#
#  Read configuration information
#

with open("model.toml", "rb") as f:

    #  Read the configuration file

    info = tomllib.load(f)

    #  Copy parameters to a new dictionary to keep name space clean

    par_names = ['r','delta','w','pk','elast','scale']
    pars = {k:info[k] for k in par_names}

    #  Get variables

    p0 = info['p']
    cap0 = info['cap0']

    #  Get run controls

    endog_p   = info['endog_p']
    base_only = info['base_only']
    force     = info['force']

    roll = info['roll']
    inertial = info['inertial']

    #  Files and directories

    idir  = info['in']

    if endog_p:
        odir = info['out_en']
        logname = 'model-en.log'
    else:
        odir = info['out_ex']
        logname = 'model-ex.log'

#
#  Start the logger
#

ql = logger(logname)

ql.log('Endogenous price',endog_p)

#
#  Look for spreadsheets defining simulations. Only try to use files
#  with names beginning with "r" and ending with ".xlsx". If base_only
#  is set, only use the baseline file
#

files = os.listdir(idir)
files = [f for f in files if f.endswith('.xlsx') and f[0]=='r']

if base_only:
    files = ['r01-baseline.xlsx']

#
#  Walk through the list of files and run any that don't have results
#  in the output directory
#

for f in files:

    #  Build the output filename

    (stem,ext) = os.path.splitext(f)

    i_name = f"{idir}/{f}"
    o_name = f"{odir}/{stem}.csv"

    #  Say what we're doing

    ql.log('Input file',i_name)

    #  See if we've already done this one

    if os.path.exists(o_name) and not base_only and not force:
        ql.log('Output file exists, skipping',o_name)
        continue

    #  Nope; read the simulation definition

    exo = pd.read_excel(i_name, index_col='period')

    #  Set the initial capital value

    run = f[:3]
    if run in roll:
        
        prior = roll[run]['base']
        roll_yrs = roll[run]['year']
        
        basefile = f'{odir}/{prior}.csv'
        roll_base = pd.read_csv(basefile,index_col='period')
        
        roll_cap0 = roll_base.at[roll_yrs,'cap']
        if 'cap0' in roll[run]:
            roll_cap0 = roll[run]['cap0']
        
        pars['cap0'] = roll_cap0

    else:
        
        pars['cap0']= cap0

    #  Set the initial price guess

    p = pd.Series(index=exo.index,data=p0)

    #  Solve the model if P needs to be endogenous

    n_it = 0

    if endog_p:

        #  If inertial, only solve for the first period

        if run in inertial:
            sol = opt.root(miss_one,p0,args=(exo,pars))
            ql.log('Max absolute miss distance',abs(sol.fun))

        #  Otherwise solve for all periods

        else:
            sol = opt.root(miss_all,p,args=(exo,pars))
            ql.log('Max absolute miss distance',max(abs(sol.fun)))

        #  Make sure it worked

        ql.log('Success',sol.success)

        assert sol.success

        #  Extract the solution

        if run in inertial:
            p = pd.Series(index=exo.index, data=sol.x[0] )
        else:
            p = pd.Series( sol.x )

    #  Evaluate it the model one more time to get the final solution whether
    #  using exogenous or endogenous prices

    d = evaluate(p,exo,pars)

    #  Handle rolling simulations by gluing these results onto the 
    #  prior run, if applicable
   
    if run in roll:

        #  shift the periods forward
        
        d.index = d.index + roll_yrs
        
        #  Merge this run onto the base run
        
        if roll_yrs > 0:
            rstack = pd.concat( [roll_base[:roll_yrs], d[:-roll_yrs]] )
        else:
            rstack = d.copy()

        #  Fix the index
        
        rstack.index = roll_base.index

        #  Move it to the expected location
        
        d = rstack

    #  Done, save the results
    
    d.to_csv(o_name)
    ql.log('Wrote',o_name)

    #  Print some summary information if this is the baseline case

    if 'baseline' in f:

        pk = pars['pk']
        w = pars['w']
        r = pars['r']
        delta = pars['delta']

        last_yr = min(d.index)

        #  For use with rolling simulations, save the capital stock at year 10

        cap10 = d.at[10,'cap']
        ql.log('Year 10 capital',cap10)

        #  For reference, calculate the ITC that produces the same investment
        #  incentive as PTC of 10%

        i_bench_sub = 0.1
        i_bench_gamma = (p**2 * d['a']**2)/(4*w)
        i_bench_gamma = i_bench_gamma.loc[last_yr]
        i_bench_itc = i_bench_gamma/((r+delta)*pk)
        i_bench_itc = i_bench_itc*(2+i_bench_sub)*i_bench_sub

        ql.log('\nInvestment benchmark ITC and sub',{
            'itc':i_bench_itc,
            'sub':i_bench_sub,
            })
