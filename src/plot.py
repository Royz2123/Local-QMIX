import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import argparse
import glob
from itertools import cycle
import os

from envs import REGISTRY as env_REGISTRY

sns.set(style='darkgrid', rc={'figure.figsize': (7.2, 4.45),
                              'text.usetex': True,
                              'xtick.labelsize': 16,
                              'ytick.labelsize': 16,
                              'font.size': 15,
                              'figure.autolayout': True,
                              'axes.titlesize': 16,
                              'axes.labelsize': 17,
                              'lines.linewidth': 2,
                              'lines.markersize': 6,
                              'legend.fontsize': 15})
colors = sns.color_palette("colorblind", 4)
# colors = sns.color_palette("Set1", 2)
# colors = ['#FF4500','#e31a1c','#329932', 'b', 'b', '#6a3d9a','#fb9a99']
dashes_styles = cycle(['-', '-.', '--', ':'])
sns.set_palette(colors)
colors = cycle(colors)

DEFAULT_COLS = {
    "learner_data": ["loss", "td_error", "grad_norm", "q_taken_mean", "target_mean"],
    "env_data": ["episode_reward"]
}


def moving_average(interval, window_size):
    if window_size == 1:
        return interval
    window = np.ones(int(window_size)) / float(window_size)
    return np.convolve(interval, window, 'same')


def plot_df(df, color, xaxis, yaxis, ma=1, label=''):
    df[yaxis] = pd.to_numeric(df[yaxis], errors='coerce')  # convert NaN string to NaN value

    mean = df.groupby(xaxis).mean()[yaxis]
    std = df.groupby(xaxis).std()[yaxis]

    if ma > 1:
        mean = moving_average(mean, ma)
        std = moving_average(std, ma)

    x = df.groupby(xaxis)[xaxis].mean().keys().values
    plt.plot(x, mean, label=label, color=color, linestyle=next(dashes_styles))
    plt.fill_between(x, mean + std, mean - std, alpha=0.25, color=color, rasterized=True)

    # plt.ylim([0,200])
    # plt.xlim([40000, 70000])


def simple_plot_df(df, color, xaxis, yaxis, ma=1, label=''):
    df.dropna(subset=[yaxis], inplace=True)
    df = df.sort_values(by=[xaxis])
    plt.plot(df[xaxis], df[yaxis], label=label, color=color, linestyle=next(dashes_styles))

    return df[xaxis], df[yaxis]


if __name__ == '__main__':
    # get args
    prs = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                  description="""Plot Traffic Signal Metrics""")
    prs.add_argument('-env', type=str, required=True, help="Enviroment Name\n")
    prs.add_argument('-exp', type=str, default=None, help="Experiment name\n")

    prs.add_argument('-l', nargs='+', default=None, help="File's legends\n")
    prs.add_argument('-t', type=str, default="", help="Plot title\n")
    prs.add_argument("-xaxis", type=str, default='t_env', help="The x axis.\n")
    prs.add_argument("-ma", type=int, default=1, help="Moving Average Window.\n")
    prs.add_argument('-sep', type=str, default=',', help="Values separator on file.\n")
    # prs.add_argument('-xlabel', type=str, default='Second', help="X axis label.\n")
    # prs.add_argument('-ylabel', type=str, default='Total waiting time (s)', help="Y axis label.\n")

    args = prs.parse_args()
    # labels = cycle(args.l) if args.l is not None else cycle([str(i) for i in range(len(args.f))])

    base_path = f"./results/"

    # Check for valid env_name
    env_name = args.env
    if args.env not in env_REGISTRY.keys():
        print("Enviroment not recognized")
        exit()
    env_path = f"{base_path}{env_name}/"

    # Check for default experiment (last)
    exp_name = args.exp
    if args.exp is None:
        exp_name = sorted(os.listdir(env_path))[-1]
    exp_path = f"{env_path}{exp_name}/"

    plt.figure()

    # File reading and grouping
    general_plots = {}
    labels = []
    for learner_name in os.listdir(exp_path):
        learner_path = f"{exp_path}{learner_name}/"
        plots_path = f"{learner_path}plots/"

        try:
            os.mkdir(plots_path)
        except OSError as e:
            pass

        if os.path.isdir(learner_path):
            labels.append(learner_name)
            for log_type_name in os.listdir(learner_path):
                log_type_name = log_type_name.split(".")[0]
                log_file = f"{learner_path}{log_type_name}.csv"
                if os.path.isfile(log_file):
                    df = pd.read_csv(log_file, sep=args.sep)

                    # Plot DataFrame
                    for col_name in DEFAULT_COLS[log_type_name]:
                        x, y = simple_plot_df(df,
                                              xaxis=args.xaxis,
                                              yaxis=col_name,
                                              label=learner_name,
                                              color=next(colors),
                                              ma=args.ma)

                        # plt.title(args.t)
                        # plt.ylabel(col_name)
                        # plt.xlabel(args.xaxis)

                        key = f"{log_type_name}_{col_name}"
                        plt.savefig(f"{plots_path}{key}_output.pdf", bbox_inches="tight")
                        plt.clf()

                        # Save data for combined plots
                        if key not in general_plots.keys():
                            general_plots[key] = []
                        general_plots[key].append((learner_name, x, y))

    # Plot combined plots and save
    plots_path = f"{exp_path}combined_plots/"

    try:
        os.mkdir(plots_path)
    except OSError as e:
        pass

    for key, data in general_plots.items():
        for learner_data in data:
            learner_name, x, y = learner_data
            plt.plot(x, y, label=learner_name, color=next(colors), linestyle=next(dashes_styles))

        plt.legend(labels)
        # plt.title(args.t)
        # plt.ylabel(key)
        # plt.xlabel(args.xaxis)

        plt.savefig(f"{plots_path}{key}_output.pdf", bbox_inches="tight")
        plt.clf()
