# --- START OF FILE analytics_plots.py ---

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import os # <<< IMPORT MỚI >>>

# <<< THÊM THAM SỐ save_dir CHO TẤT CẢ CÁC HÀM >>>

def plot_convergence(history: dict, save_dir: str = None):
    fig, ax1 = plt.subplots(figsize=(15, 7))
    color = 'tab:blue'
    ax1.set_xlabel('Iteration')
    ax1.set_ylabel('Cost', color=color)
    ax1.plot(history['iteration'], history['best_cost'], label='Best Cost', color='green', linewidth=2.5)
    ax1.plot(history['iteration'], history['current_cost'], label='Current Cost', color='cornflowerblue', alpha=0.6)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.legend(loc='upper left')
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Temperature', color=color)
    ax2.plot(history['iteration'], history['temperature'], label='Temperature', color=color, linestyle='--', alpha=0.8)
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.legend(loc='upper right')
    fig.tight_layout()
    plt.title('Algorithm Convergence', fontsize=16)
    if save_dir: plt.savefig(os.path.join(save_dir, "1_convergence.png"))

def plot_acceptance_criteria(history: dict, save_dir: str = None):
    plt.figure(figsize=(8, 8))
    move_counts = pd.Series(history['accepted_move_type']).value_counts()
    colors = {'new_best': 'gold', 'better': 'limegreen', 'sa_accepted': 'coral', 'rejected': 'lightgrey'}
    plt.pie(move_counts, labels=move_counts.index, autopct='%1.1f%%', startangle=140,
            colors=[colors.get(key, 'gray') for key in move_counts.index])
    plt.title('Move Acceptance Distribution', fontsize=16)
    plt.ylabel('')
    if save_dir: plt.savefig(os.path.join(save_dir, "2_acceptance_criteria.png"))

def plot_operator_weights(operator_history: dict, save_dir: str = None):
    if not operator_history['iteration']: return
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), sharex=True)
    destroy_df = pd.DataFrame(operator_history['destroy_weights'])
    for op_name in destroy_df.columns:
        ax1.plot(operator_history['iteration'], destroy_df[op_name], label=op_name, marker='o', markersize=4)
    ax1.set_title('Destroy Operator Weights Evolution', fontsize=14)
    ax1.set_ylabel('Weight')
    ax1.legend(); ax1.grid(True, linestyle=':', alpha=0.6)
    repair_df = pd.DataFrame(operator_history['repair_weights'])
    for op_name in repair_df.columns:
        ax2.plot(operator_history['iteration'], repair_df[op_name], label=op_name, marker='o', markersize=4)
    ax2.set_title('Repair Operator Weights Evolution', fontsize=14)
    ax2.set_xlabel('Iteration'); ax2.set_ylabel('Weight')
    ax2.legend(); ax2.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    fig.suptitle('Operator Weight Evolution', fontsize=18, y=1.02)
    if save_dir: plt.savefig(os.path.join(save_dir, "3_operator_weights.png"))

def plot_destroy_impact(history: dict, save_dir: str = None):
    plt.figure(figsize=(15, 7))
    df = pd.DataFrame(history)
    palette = {'new_best': 'gold', 'better': 'limegreen', 'sa_accepted': 'coral', 'rejected': 'lightgrey'}
    sns.scatterplot(
        data=df, x='iteration', y='q_removed', hue='accepted_move_type',
        palette=palette, size='is_large_destroy', sizes=(40, 150),
        alpha=0.7, edgecolor='black', linewidth=0.5
    )
    plt.title('Destroy Impact Analysis', fontsize=16)
    plt.xlabel('Iteration')
    plt.ylabel('Number of Customers Removed (q)')
    plt.legend(title='Move Type'); plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    if save_dir: plt.savefig(os.path.join(save_dir, "4_destroy_impact.png"))

# --- END OF FILE analytics_plots.py ---