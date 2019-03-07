import pickle
import pystan
import os
import pandas as pd
import utils.data_processing as dp

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
    ax1.hist(tearo_trunc_fit['y_pred'], bins=100, density=True);
    ax1.set_title('Model accessibility values for %s'.format(suburb_name));

    ax2.hist(tearo['accessibility'], bins=100, density=True);
    ax2.set_title('Raw accessibility values for %s'.format(suburb_name));
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

    # Do the Training
    partial_pool_data = {'N': len(df),
                         'level': level+1, # Stan counts starting at 1,
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
