import pickle
import pystan
import os
import pandas as pd
import utils.data_processing as dp
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

def save(obj, filename):
    """Save compiled models for reuse."""
    with open(filename, 'wb') as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)


def load(filename):
    """Reload compiled models for reuse."""
    return pickle.load(open(filename, 'rb'))


def load_or_generate_stan_model(model_folder,
                                model='univariate_normal'):
    """
    Loads saved Stan Model or compiles and saves Stan Model
    """
    pkl_file = model_folder + '/' + model + '.pkl'
    stan_file = model_folder + '/' + model + '.stan'

    print(pkl_file)
    if os.path.isfile(pkl_file):
        sm = pickle.load(open(pkl_file, 'rb'))
    else:
        sm = pystan.StanModel(file= stan_file)
        with open(pkl_file, 'wb') as f:
            pickle.dump(sm, f)
    return sm


# Generate mapping from sizechart name to ID
def convert_categorical_to_ID(df, level):
    level_values = df[level].unique()
    level_lookup = dict(zip(level_values, range(len(level_values))))
    level_lookup_df = pd.DataFrame({'level_id': level_lookup.values(),
                                    'level': level_lookup.keys()})

    new_col = level+'_id'
    level = df[new_col] = df[level].replace(level_lookup).values
    return df


############################
## SUMMARIES AND PLOTTING ##
############################

def summarise_variable(stanfit, var):
    summ = stanfit.summary([var])
    summ_df = pd.DataFrame(summ['summary'],
                           columns=(u'mean', u'se_mean', u'sd',
                                    u'hpd_2.5',u'hpd_25',
                                    u'hpd_50',u'hpd_75',u'hpd_97.5',
                                    u'n_eff',u'Rhat'),
                           index=summ['summary_rownames']).reset_index()
    return summ_df



def run_plot_suburb_stan(df, model, suburb_name='Karori'):
    """
    Sample from lower truncated normal model for mean and sd
    of suburban accessibility.
    Args:
     df: accessibility df containing suburb name
     model: compiled and loaded Stan model
     suburb_name=: Default of 'Karori'.
    Returns:
     plot of raw vs. modelled values of accessibiity
    """

    # Set up data
    suburb_df = df[df['suburb'] == suburb_name]
    suburb_df_dat = {'N': suburb_df.shape[0],
                     'L': 0,
                     'U': 80,
                     'y': suburb_df['accessibility'].values,}

    # Run Stan model for suburb
    suburb_trunc_fit = model.sampling(suburb_df_dat, chains=4)

    # Plot model posterior predictive against raw values
    fig, (ax1, ax2) = plt.subplots(ncols=2, sharex=True, sharey=True, figsize=(8,6))
    ax1.hist(suburb_trunc_fit['y_pred'], bins=100, density=True);
    ax1.set_title('Model accessibility values for {:s}'.format(suburb_name));

    ax2.hist(suburb_df['accessibility'], bins=100, density=True);
    ax2.set_title('Raw accessibility values for {:s}'.format(suburb_name));

    plt.xlim(0,80)
    return


def run_plot_suburb(df, model, suburb_name='Karori'):
    """
    Sample from lower truncated normal model for mean and sd
    of suburban accessibility.
    Args:
     df: accessibility df containing suburb name
     model: compiled and loaded Stan model
     suburb_name=: Default of 'Karori'.
    Returns:
     plot of raw vs. modelled values of accessibiity
    """

    # Set up data
    suburb_df = df[df['suburb'] == suburb_name]
    suburb_df_dat = {'N': suburb_df.shape[0],
                     'L': 0,
                     'U': 80,
                     'y': suburb_df['accessibility'].values,}

    # Run Stan model for suburb
    suburb_trunc_fit = model.sampling(suburb_df_dat, chains=4)

    # Plot model posterior predictive against raw values
    fig, (ax1, ax2) = plt.subplots(ncols=2, sharex=True, sharey=True, figsize=(8,6))
    ax1.hist(suburb_trunc_fit['y_pred'], bins=100, density=True);
    ax1.set_title('Model accessibility values for {:s}'.format(suburb_name));

    ax2.hist(suburb_df['accessibility'], bins=100, density=True);
    ax2.set_title('Raw accessibility values for {:s}'.format(suburb_name));

    plt.xlim(0,80)
    return


def train_acc_hierarchical(df, normal_model, level='suburb',
                           return_stanfit=False, return_levels_stanfit=False):
    """
    Single level is sizechart at the moment. Should I make it more flexible?
    Yes, Try out a brand level one?
    """
    # Generate mapping from sizechart name to ID
    level_values = df[level].unique()
    level_lookup = dict(zip(level_values, range(len(level_values))))
    level_lookup_df = pd.DataFrame({'level_id': list(level_lookup.values()),
                                    'level': list(level_lookup.keys())})

    level = df['level_id'] = (df[level]
                              .replace(dp.replace_categorical_with_int(df, level)).values)

    df = pd.merge(df,
                     (df
                     .groupby(['level_id'])
                     .size()
                     .reset_index(name='samples')))

    # Run the model
    partial_pool_data = {'N': len(df),
                         'level': df['level_id']+1, # Stan counts starting at 1,
                         'L': len(level_values),
                         'l': 0,
                         'y': df['accessibility']}

    partial_pool_fit = normal_model.sampling(data=partial_pool_data,
                                             iter=1000,
                                             chains=1,
                                             seed=344)

    if return_stanfit:
        return partial_pool_fit

    if return_levels_stanfit:
        return {'stanfit': partial_pool_fit,
                'level_id': level_lookup.values(),
                'level_lookup': level_lookup.keys()}


def df_for_forestplot(stanfit, df,  param_to_plot, param_categorical):
    # Generate summary for parameter of interest
    summ = stanfit.summary([param_to_plot])
    summ_df = pd.DataFrame(summ['summary'],
                       columns=(u'mean', u'se_mean', u'sd', u'hpd_2.5',u'hpd_25',
                                u'hpd_50',u'hpd_75',u'hpd_97.5',u'n_eff',u'Rhat'),
                       index=summ['summary_rownames']).reset_index()
    # summ_df = summ_df.sort_values('mean')
    summ_df['ypos'] = np.arange(len(summ_df))

    # Map ID to plot
    summ_df = pd.merge(summ_df,
                   (df[[param_categorical.split('_id')[0], param_categorical]]
                    .drop_duplicates().rename(columns={param_categorical: 'ypos'})))
    return summ_df


def custom_forestplot(df, param_categorical,
                      size=8, aspect=0.8, facetby=None,
                      avg_min=None, avg_max=None):
    ''' Conv fn: plot features from Fit summary using seaborn
        Facet on sets of forests for comparison
        Borrowed from http://blog.applied.ai/bayesian-inference-with-pymc3-part-3/'''

    g = sns.FacetGrid(col=facetby, hue='mean', data=df, palette='RdBu_r'
                      ,size=size, aspect=aspect)
    _ = g.map(plt.scatter, 'mean', param_categorical
                ,marker='o', s=100, edgecolor='#333333', linewidth=0.8, zorder=10)
    _ = g.map(plt.hlines, param_categorical, 'hpd_2.5','hpd_97.5', color='#aaaaaa')

    _ = g.axes.flat[0].set_ylabel(param_categorical)
    _ = [ax.set_xlabel('coeff value') for ax in g.axes.flat]
    _ = g.axes.flat[0].set_yticklabels(df[param_categorical])
    if avg_min is not None:
        plt.axvspan(avg_min, avg_max, alpha=0.1, color='black')
    return
