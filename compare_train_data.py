# -*- coding: utf-8 -*-
"""

Author:   Metin Bicer
email:    m.bicer19@imperial.ac.uk

Compare synthetic datasets, for the train subjects generated by the conditional
GANs presented in the paper, to the experimental dataset

This file can directly be run to reproduce the results in the paper.

Alternatively, conditional_compare_ranges function can be imported and used
with different settings (ranges for the conditions etc)

"""
import numpy as np
from utils import get_real_data, get_synthetic_grfm, spmInverse, spmGRF
from utils import read_dataframes, filterGRFTensor
from matplotlib import rc

rc('text', usetex=True)

AGE = [26, 40]
MASS = [57, 74]
LEG = [868, 931]
SPEED = [0.81, 1.67]
GENDER = [0, 0.5]
RANGES_CONSTRAINED = {'age': AGE, 'mass':MASS, 'leglength_static':LEG,
                      'walking_speed':SPEED, 'gender_int':GENDER}

MODELS = ['gcgan', 'acgan', 'llcgan', 'mcgan', 'wscgan', 'multicgan']

AGE = [19, 64]
MASS = [50.7, 95]
LEG = [804.4, 1075.5]
SPEED = [0.178, 2.042]
GENDER = [0, 1]
RANGES_ENTIRE = {'age': AGE, 'mass':MASS, 'leglength_static':LEG,
                 'walking_speed':SPEED, 'gender_int':GENDER}

def conditional_compare_ranges(models, is_entire=False, seeds=[0,1],
                               plot=False, save=False, save_name='',
                               save_generated=False, plot_individual=False):
    """
    compare synthetic datasets generated by cGANs to the experimental dataset
    using the spm1d package

    Args:
        models (list): list of strings defining model names.
        is_entire (bool): True to compare to the entire experimental dataset.
                          False to compare to the range given in RANGES_CONSTRAINED.
        seeds (list): list of integers to be used in random seed.
        plot (bool): whether or not to plot the results.
        save (bool): whether or not to save the plots.
        save_name (str): Name used to save plot.
        plot_individual (bool): True to plot individual waveforms.

    Returns:
        synthetic_ik (TYPE): DESCRIPTION.
        synthetic_grf (TYPE): DESCRIPTION.
        real_ik (TYPE): DESCRIPTION.
        real_grf (TYPE): DESCRIPTION.

    """
    model_ranges = RANGES_CONSTRAINED
    data_fold = 'constrained'
    if is_entire:
        model_ranges = RANGES_ENTIRE
        data_fold = 'entire'
    # defaults
    features_ik = np.array(['pelvis_tilt', 'pelvis_list', 'pelvis_rotation',
                            'hip_flexion_r', 'hip_adduction_r', 'hip_rotation_r',
                            'knee_angle_r', 'ankle_angle_r'])
    features_grf = np.array(['ground_force_1_vx', 'ground_force_1_vy',
                             'ground_force_1_vz', 'ground_moment_1_my'])

    subject_nos = 'all'
    trial_no = 'all'
    plot_field_ik = 'ik_gc'
    plot_field_grf = 'grf_2d_gc'
    feature_names_field_ik = 'ik_names'
    feature_names_field_grf = 'grf_names_2d'
    divide_by = False
    # experimental data
    data_df = read_dataframes(['data/data_1.pickle', 'data/data_2.pickle'])
    excluded_subjects = [2014001, 2014003, 2015042]
    data_df_train = data_df[~data_df.subject.isin(excluded_subjects)].reset_index(drop=True)
    ik_inds = [18, 26]
    grfy_inds = [15, 16, 17]

    print('Spm1d -- Synthetic vs Experimental Data')
    print(f'\n{"Conditions":<10s}{"IK":>12s}{"GRF":>12s}{"TOTAL":>12s}')
    idxs = None
    for field, ranges in model_ranges.items():
        if idxs is None:
            idxs = (data_df_train[field]>=ranges[0])&(data_df_train[field]<=ranges[1])
            continue
        # else
        idxs = idxs&(data_df_train[field]>=ranges[0])&(data_df_train[field]<=ranges[1])
    # get the part within the given ranges
    data_df_train_range = data_df_train[idxs].reset_index(drop=True)
    # get all ik and grf data
    real_ik = get_real_data(data_df_train_range, trial_no, subject_nos, features_ik,
                              plot_field_ik, feature_names_field_ik, divide_by,
                              'age', 0, 10e6)
    real_grf = get_real_data(data_df_train_range, trial_no, subject_nos, features_grf,
                              plot_field_grf, feature_names_field_grf, divide_by,
                              'age', 0, 10e6)
    # body weight and normalized forces
    bws = 9.81*data_df_train_range['mass'].values[:,None,None]
    for model in models:
        # pre allocate
        tot_ik = []
        tot_grf = []
        tot_diff = []
        for seed in seeds:
            file = f'seed{seed}.npy'
            synthetic_data = np.load(f'Results/{model}/{data_fold}/{file}')
            synthetic_ik = synthetic_data[:, 0, :, ik_inds[0]:ik_inds[1]]
            # filter forces
            synthetic_data[:,:,:,grfy_inds] = filterGRFTensor(synthetic_data[:,:,:,grfy_inds],
                                                              100, 20, 2,
                                                              10, 1, 0)
            synthetic_grf = get_synthetic_grfm(synthetic_data, grfy_inds[0])
            plot_name = f'Results/{model}/{save_name}_SPM'
            if model == 'm' or 'multi' in model:
                real_grf_norm = real_grf/bws
                synthetic_grf /= bws
                diff_grf, toeoff, _ = spmGRF(real_grf_norm, synthetic_grf,
                                             1, plot, save, 'b', 'r', 'grey',
                                             True, plot_individual,
                                             plot_name+'_GRF', return_comp_diffs=False)
            else:
                diff_grf, toeoff, _ = spmGRF(real_grf, synthetic_grf,
                                             1, plot, save, 'b', 'r', 'grey',
                                             False, plot_individual,
                                             plot_name+'_GRF', return_comp_diffs=False)
            tot_grf.append(diff_grf)
            diff_ik = spmInverse(real_ik, synthetic_ik, 'ik', toeoff, None,
                                 plot, save, False, None, 'b', 'r', 'grey',
                                 plot_name, plot_individual=plot_individual,
                                 return_comp_diffs=False)[0]
            tot_ik.append(diff_ik)
            # total ik+grf
            ik_grf_diff = diff_ik*real_ik.shape[-1] + diff_grf*real_grf.shape[-1]
            tot_diff.append(ik_grf_diff/(real_ik.shape[-1] + real_grf.shape[-1]))

        # printing
        if len(tot_ik)==1:
            print(f'{model:<10s}{np.mean(tot_ik):>12.1f}{np.mean(tot_grf):>12.1f}{np.mean(tot_diff):>12.1f}')
        if len(tot_ik)>1:

            t = f'{model:<10s}'
            t1 = f'{np.mean(tot_ik):.1f}±{np.std(tot_ik):<.1f}'
            t += f'{t1:>12s}'
            t1 = f'{np.mean(tot_grf):.1f}±{np.std(tot_grf):<.1f}'
            t += f'{t1:>12s}'
            t1 = f'{np.mean(tot_diff):.1f}±{np.std(tot_diff):<.1f}'
            t += f'{t1:>12s}'
            print(t)
    return synthetic_ik, synthetic_grf, real_ik, real_grf


if __name__ == '__main__':
    # entire dataset analysis
    _ = conditional_compare_ranges(MODELS, is_entire=True, seeds=range(6))
    # constrained dataset analysis
    _ = conditional_compare_ranges(MODELS, is_entire=False, seeds=range(6))