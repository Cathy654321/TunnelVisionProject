import matplotlib.pyplot as plt

def plot_case_results(results):

    total_points = len(results)
    num_points_to_plot = 10
    step = total_points // num_points_to_plot

    indices = list(range(0, total_points, step))[:num_points_to_plot]

    rounds = [i + 1 for i in indices]
    aspe_vals = [results[i]['ASPE'] for i in indices]
    case_vals = [results[i]['CASE'] for i in indices]
    aspect_coverage_vals = [results[i]['AspectCoverage (C)'] for i in indices]

    plt.figure(figsize=(10, 6))

    plt.plot(rounds, aspe_vals, label='ASPE', marker='o')
    plt.plot(rounds, case_vals, label='CASE', marker='s')

    plt.xlabel("Timestep", fontsize=16, labelpad=10)
    plt.ylabel("Metric Value", fontsize=16, labelpad=10)

    plt.tick_params(axis='both', labelsize=12)

    plt.grid(True)
    plt.legend(
        title="Event",
        loc="upper right",
        fontsize=12,
        title_fontsize=16,
        markerscale=1.8,
        borderpad=1.2,
        labelspacing=1.0,
        handlelength=3.0
    )
    plt.tight_layout()
    plt.show()
