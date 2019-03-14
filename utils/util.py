
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# MOVE TO UTILS
# Conversion functions
def hiking_speed(grade, params_list):
    W = params_list[0]*np.exp(- params_list[1]* np.abs(grade + params_list[2]))
    return W

def flat_travel_time(distance, speed=5.0):
    time_hr = (distance / 1000) / speed
    time_mins = time_hr * 60.0
    return time_mins

def hiking_time(grade, distance, params_list):
    W = params_list[0]*np.exp(- params_list[1]* np.abs(grade + params_list[2]))
    time_hr = (distance / 1000) / W
    time_mins = time_hr * 60.0
    return time_mins

def vertical_average_lines(x, **kwargs):
    """
    Utility function to plot median and mean lines
    Also adds a legend with the values of the mean and median
    To be used within a map function for seaborn FacetGrid

    Args:
     x: Variable plotted on histogram. Called as string in map
     **kwargs: Additional parameters set in FacetGrid.

    Returns:
     Plots and labels mean and median averages.
    """

    plt.axvline(x.mean(), color='r',
                label= 'Mean = '+str(int(x.mean())))
    plt.axvline(x.median(),
                color='k',
                ls='--',
                label='Median = '+str(int(x.median())))
    plt.legend(loc='upper right')
    return
