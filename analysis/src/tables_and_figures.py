# results dir and methods
import os
from pathlib import Path
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from .utils import DTO
import shutil
from .utils import is_pareto_efficient, mkdirs

import numpy as np

def retrive_results(
    dataset,
    log_dir="results"
):
    """retrive loaded results of a dataset from files

    Args:
        dataset (str): dataset name, e.g. Moji, Bios_both, and Bios_gender
        log_dir (str, optional): _description_. Defaults to "results".

    Returns:
        dict: experimental result dataframes of different methods.
    """
    log_dir = Path(log_dir)
    results = {}
    for root, dirs, files in os.walk(log_dir):
        for file in files:
            if file.startswith(dataset):
                pre_len = len(dataset)+len(str(log_dir))+2
                file_path = os.path.join(root, file)
                mehtod = str(os.path.join(root, file))[pre_len:-7]
                results[mehtod] = pd.read_pickle(file_path)
    return results


def final_results_df(
    results_dict,
    model_order = None,
    Fairness_metric_name = "fairness",
    Performance_metric_name = "performance",
    pareto = True,
    pareto_selection = "test",
    selection_criterion = "DTO",
    return_dev = True,
    Fairness_threshold = 0.0,
    Performance_threshold = 0.0,
    return_conf = False,
    save_conf_dir = None,
    num_trail = None,
    ):
    """Process the results to a single dataset from creating tables and plots.

    Args:
        results_dict (dict): retrived results dictionary, which is typically the returned dict from function `retrive_results`
        model_order (list, optional): a list of models that will be considered in the final df. Defaults to None.
        Fairness_metric_name (str, optional): the metric name for fairness evaluation. Defaults to "rms_TPR".
        Performance_metric_name (str, optional): the metric name for performance evaluation. Defaults to "accuracy".
        pareto (bool, optional): whether or not to return only the Pareto frontiers. Defaults to True.
        pareto_selection (str, optional): which split is used to select the frontiers. Defaults to "test".
        selection_criterion (str, optional): model selection criteria, one of {performance, fairness, both (DTO)} . Defaults to "DTO".
        return_dev (bool, optional): whether or not to return dev results in the df. Defaults to True.
        Fairness_threshold (float, optional): filtering rows with a minimal fairness as the threshold. Defaults to 0.0.
        Performance_threshold (float, optional): filtering rows with a minimal performance as the threshold. Defaults to 0.0.
        return_conf (bool, optional): return the selected epoch and corresponding YAML configure files if True. Defaults to False.
        save_conf_dir (str, optional): save selected epoch and configure files to the dir. Defaults to None.

    Returns:
        pandas.DataFrame: selected results of different models for report
    """

    df_list = []
    for key in (results_dict.keys() if model_order is None else model_order):
        _df = results_dict[key]

        # Calculate Mean and Variance for each run
        agg_dict = {
            "dev_performance":["mean", "std"],
            "dev_fairness":["mean", "std"],
            "test_performance":["mean", "std"],
            "test_fairness":["mean", "std"],
            "epoch":list,
            "opt_dir":list,
            }
        try:
            _df = _df.groupby(_df.index).agg(agg_dict).reset_index()
        except:
            print(key)
            break

        _df.columns = [' '.join(col).strip() for col in _df.columns.values]

        if num_trail is not None:
            _df = _df.sample(n=min(int(num_trail), len(_df)), random_state=1)

        # Select Pareto Frontiers
        if pareto:
            _pareto_flag = is_pareto_efficient(
                -1*_df[["{}_{} mean".format(pareto_selection, Fairness_metric_name), "{}_{} mean".format(pareto_selection, Performance_metric_name)]].to_numpy()
                )
            _pareto_df = _df[_pareto_flag].copy()
        else:
            _pareto_df = _df.copy()

        # Filtering based on min fairness and performance
        _tmp_df = _pareto_df[_pareto_df["dev_{} mean".format(Performance_metric_name)]>=Performance_threshold].copy()
        _tmp_df = _tmp_df[_tmp_df["dev_{} mean".format(Fairness_metric_name)]>=Fairness_threshold].copy()

        if len(_tmp_df) >= 1:
            _pareto_df = _tmp_df
        
        # Rename and reorder the columns
        selected_columns = ["{}_{} {}".format(phase, metric, value) for phase in ["test", "dev"] for metric in [Performance_metric_name, Fairness_metric_name] for value in ["mean", "std"]]
        selected_columns.append("epoch list")
        selected_columns.append("opt_dir list")

        _pareto_df = _pareto_df[selected_columns].copy()
        _pareto_df["Models"] = [key]*len(_pareto_df)

        _final_DTO = DTO(
            fairness_metric=list(_pareto_df["dev_{} mean".format(Fairness_metric_name)]), 
            performacne_metric=list(_pareto_df["dev_{} mean".format(Performance_metric_name)]),
            utopia_fairness = 1, utopia_performance = 1
            )
        _pareto_df["dev_DTO mean"] = _final_DTO

        # Model selection
        if selection_criterion is not None:
            if selection_criterion == "DTO":
                selected_epoch_id = np.argmin(_pareto_df["dev_{} mean".format(selection_criterion)])
            else:
                selected_epoch_id = np.argmax(_pareto_df["dev_{} mean".format(selection_criterion)])
            _pareto_df = _pareto_df.iloc[[selected_epoch_id]].copy()
        
        df_list.append(_pareto_df)

    final_df = pd.concat(df_list)
    final_df.reset_index(inplace=True)

    if selection_criterion is not None:
        _over_DTO = DTO(
            fairness_metric=list(final_df["test_{} mean".format(Fairness_metric_name)]), 
            performacne_metric=list(final_df["test_{} mean".format(Performance_metric_name)]),
            utopia_fairness = 1, utopia_performance = 1
            )
        final_df["DTO"] = _over_DTO

        if save_conf_dir is not None:
            for (_model, _epoch_list, opt_list) in final_df[["Models", "epoch list", "opt_dir list"]].values:
                model_dir = Path(save_conf_dir)/_model
                mkdirs(model_dir)
                for _run, (_epoch, _opt) in enumerate(zip(_epoch_list, opt_list)):
                    shutil.copy2(_opt, model_dir / 'Run_{}_Selected_Epoch_{}.yaml'.format(_run, _epoch))

        evaluation_cols = list(final_df.keys())[1:(9 if return_dev else 5)]
        reproducibility_cols = ["epoch list", "opt_dir list"] if return_conf else []
        final_df = final_df[["Models"]+evaluation_cols+["DTO"]+reproducibility_cols].copy()

    return final_df