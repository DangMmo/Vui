# src/utils/plotter.py
from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import os

from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from ..core.data_structures import Solution, ProblemInstance

# ==============================================================================
# SECTION 1: VISUALIZATION OF THE SOLUTION ITSELF
# ==============================================================================

def _get_unique_nodes_from_fe_schedule(schedule: List[Dict]) -> List[int]:
    """Hàm nội bộ để trích xuất đường đi duy nhất từ lịch trình FE."""
    if not schedule:
        return []
    path_nodes = [schedule[0]['node_id']]
    for event in schedule[1:]:
        if event['node_id'] != path_nodes[-1]:
            path_nodes.append(event['node_id'])
    return path_nodes

def plot_solution_visualization(solution: "Solution", save_dir: str):
    """
    Vẽ bản đồ trực quan hóa lời giải 2E-VRP, bao gồm các routes và các điểm.
    """
    if not solution:
        print("Warning: Cannot plot visualization for an empty solution.")
        return

    problem = solution.problem
    fig, ax = plt.subplots(figsize=(20, 16))

    # Lấy màu cho các FE route
    num_fe_routes = len(solution.fe_routes)
    fe_route_colors = plt.cm.get_cmap('tab20', num_fe_routes if num_fe_routes > 0 else 1)

    # Map màu từ FE route tới SE route thông qua satellite
    satellite_to_color_map: Dict[int, any] = {}
    for i, fe_route in enumerate(solution.fe_routes):
        color = fe_route_colors(i)
        for se_route in fe_route.serviced_se_routes:
            satellite_to_color_map[se_route.satellite.id] = color

    # Vẽ các điểm (nodes)
    ax.scatter([c.x for c in problem.customers], [c.y for c in problem.customers], c='cornflowerblue', marker='o', s=50, label='Customer', zorder=3)
    ax.scatter([s.x for s in problem.satellites], [s.y for s in problem.satellites], c='limegreen', marker='s', s=150, label='Satellite', edgecolors='black', zorder=4)
    ax.scatter(problem.depot.x, problem.depot.y, c='black', marker='*', s=500, label='Depot', edgecolors='white', zorder=5)

    # Thêm ID cho các điểm
    for node in problem.node_objects.values():
        ax.text(node.x, node.y + 1, str(node.id), fontsize=9, ha='center')

    # Vẽ các SE routes
    for se_route in solution.se_routes:
        color = satellite_to_color_map.get(se_route.satellite.id, 'gray')
        path_node_ids = [nid % problem.total_nodes for nid in se_route.nodes_id]
        path_coords = [(problem.node_objects[nid].x, problem.node_objects[nid].y) for nid in path_node_ids]
        x_coords, y_coords = zip(*path_coords)
        ax.plot(x_coords, y_coords, color=color, linestyle='-', linewidth=1.2, alpha=0.8, zorder=1)

    # Vẽ các FE routes
    for i, fe_route in enumerate(solution.fe_routes):
        color = fe_route_colors(i)
        path_node_ids = _get_unique_nodes_from_fe_schedule(fe_route.schedule)
        if not path_node_ids:
            continue
        path_coords = [(problem.node_objects[nid].x, problem.node_objects[nid].y) for nid in path_node_ids]
        x_coords, y_coords = zip(*path_coords)
        ax.plot(x_coords, y_coords, color=color, linestyle='--', linewidth=3, alpha=0.9, zorder=2)

    # Cấu hình biểu đồ
    ax.set_title(f"2E-VRP Solution Visualization (Total Cost: {solution.get_objective_cost():.2f})", fontsize=18)
    ax.set_xlabel("X Coordinate", fontsize=12)
    ax.set_ylabel("Y Coordinate", fontsize=12)
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_aspect('equal', adjustable='box')

    plt.tight_layout()

    # Lưu file
    file_path = os.path.join(save_dir, "solution_visualization.png")
    plt.savefig(file_path, dpi=300)
    print(f"  - Solution visualization saved to {file_path}")


# ==============================================================================
# SECTION 2: PLOTTING OF ALGORITHM PERFORMANCE HISTORY
# ==============================================================================

def _plot_convergence(history: dict, save_dir: str):
    """Vẽ biểu đồ hội tụ của chi phí và nhiệt độ."""
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
    plt.savefig(os.path.join(save_dir, "1_convergence.png"), dpi=300)

def _plot_acceptance_criteria(history: dict, save_dir: str):
    """Vẽ biểu đồ tròn phân phối các loại nước đi được chấp nhận."""
    plt.figure(figsize=(8, 8))
    move_counts = pd.Series(history['accepted_move_type']).value_counts()
    colors = {'new_best': 'gold', 'better': 'limegreen', 'sa_accepted': 'coral', 'rejected': 'lightgrey'}
    
    if not move_counts.empty:
        plt.pie(move_counts, labels=move_counts.index, autopct='%1.1f%%', startangle=140,
                colors=[colors.get(key, 'gray') for key in move_counts.index])
        plt.title('Move Acceptance Distribution', fontsize=16)
        plt.ylabel('')
        plt.savefig(os.path.join(save_dir, "2_acceptance_criteria.png"), dpi=300)
    else:
        print("  - Skipping acceptance criteria plot (no data).")


def _plot_operator_weights(operator_history: dict, save_dir: str):
    """Vẽ biểu đồ tiến hóa trọng số của các toán tử."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), sharex=True)
    
    # Destroy operators
    destroy_df = pd.DataFrame(operator_history['destroy_weights'])
    for op_name in destroy_df.columns:
        ax1.plot(operator_history['iteration'], destroy_df[op_name], label=op_name, marker='o', markersize=4, alpha=0.8)
    ax1.set_title('Destroy Operator Weights Evolution', fontsize=14)
    ax1.set_ylabel('Weight')
    ax1.legend()
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    # Repair operators
    repair_df = pd.DataFrame(operator_history['repair_weights'])
    for op_name in repair_df.columns:
        ax2.plot(operator_history['iteration'], repair_df[op_name], label=op_name, marker='o', markersize=4, alpha=0.8)
    ax2.set_title('Repair Operator Weights Evolution', fontsize=14)
    ax2.set_xlabel('Iteration')
    ax2.set_ylabel('Weight')
    ax2.legend()
    ax2.grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.suptitle('Operator Weight Evolution', fontsize=18)
    plt.savefig(os.path.join(save_dir, "3_operator_weights.png"), dpi=300)

def _plot_destroy_impact(history: dict, save_dir: str):
    """Vẽ biểu đồ phân tích tác động của các lần phá hủy."""
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
    plt.legend(title='Move Type')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "4_destroy_impact.png"), dpi=300)

def plot_customer_clusters(problem: "ProblemInstance", labels: list, save_dir: str):
    """
    Vẽ biểu đồ phân tán thể hiện các cụm khách hàng.
    """
    print("\nGenerating customer cluster visualization...")
    plt.figure(figsize=(15, 12))
    
    customer_data = {
        'x': [c.x for c in problem.customers],
        'y': [c.y for c in problem.customers],
        'cluster_id': labels
    }
    df = pd.DataFrame(customer_data)
    
    sns.scatterplot(
        data=df, x='x', y='y', hue='cluster_id',
        palette='viridis', s=40, alpha=0.9, legend='full'
    )
    
    plt.scatter(
        [s.x for s in problem.satellites], [s.y for s in problem.satellites],
        s=150, c='red', marker='^', edgecolor='black', label='Satellites'
    )
    
    plt.scatter(
        problem.depot.x, problem.depot.y,
        s=300, c='gold', marker='*', edgecolor='black', label='Depot'
    )

    plt.title(f'Customer Clustering (k={len(set(labels))})')
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.legend(title='Cluster ID / Node')
    plt.axis('equal')
    plt.grid(True, linestyle=':', alpha=0.6)
    
    file_path = os.path.join(save_dir, "0_customer_clusters.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    print(f"Cluster visualization saved to {file_path}")


def plot_solution_visualization(solution: "Solution", save_dir: str):
    """
    Vẽ bản đồ lời giải (NÂNG CẤP: tên file và tiêu đề động).
    """
    problem = solution.problem
    fig, ax = plt.subplots(figsize=(20, 16))

    num_fe_routes = len(solution.fe_routes)
    fe_route_colors = plt.cm.get_cmap('tab20', num_fe_routes if num_fe_routes > 0 else 1)

    satellite_to_color_map: Dict[int, any] = {}
    for i, fe_route in enumerate(solution.fe_routes):
        color = fe_route_colors(i)
        for se_route in fe_route.serviced_se_routes:
            satellite_to_color_map[se_route.satellite.id] = color

    ax.scatter([c.x for c in problem.customers], [c.y for c in problem.customers], c='cornflowerblue', marker='o', s=50, label='Customer')
    ax.scatter([s.x for s in problem.satellites], [s.y for s in problem.satellites], c='limegreen', marker='s', s=150, label='Satellite', edgecolors='black')
    ax.scatter(problem.depot.x, problem.depot.y, c='black', marker='*', s=500, label='Depot', edgecolors='white')

    for node in problem.node_objects.values():
        ax.text(node.x, node.y + 1, str(node.id), fontsize=9, ha='center')

    for se_route in solution.se_routes:
        color = satellite_to_color_map.get(se_route.satellite.id, 'gray')
        path_node_ids = [nid % problem.total_nodes for nid in se_route.nodes_id]
        path_coords = [(problem.node_objects[nid].x, problem.node_objects[nid].y) for nid in path_node_ids]
        x_coords, y_coords = zip(*path_coords)
        ax.plot(x_coords, y_coords, color=color, linestyle='-', linewidth=1.2, alpha=0.8)

    for i, fe_route in enumerate(solution.fe_routes):
        color = fe_route_colors(i)
        path_node_ids = _get_unique_nodes_from_fe_schedule(fe_route.schedule)
        if not path_node_ids: continue
        path_coords = [(problem.node_objects[nid].x, problem.node_objects[nid].y) for nid in path_node_ids]
        x_coords, y_coords = zip(*path_coords)
        ax.plot(x_coords, y_coords, color=color, linestyle='--', linewidth=3, alpha=0.9)
    
    # --- PHẦN NÂNG CẤP ---
    title = getattr(solution, 'custom_title', f"Final Merged Solution (Total Cost: {solution.get_objective_cost():.2f})")
    ax.set_title(title, fontsize=18)
    
    ax.set_xlabel("X Coordinate", fontsize=12)
    ax.set_ylabel("Y Coordinate", fontsize=12)
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_aspect('equal', adjustable='box')
    
    plt.tight_layout()

    # --- PHẦN NÂNG CẤP ---
    cluster_id_str = ""
    if "Cluster" in title:
        try:
            # Tách số ID từ chuỗi "Solution for Cluster 0 (Cost: ...)"
            cluster_id_str = f"cluster_{title.split('Cluster ')[1].split(' ')[0]}"
        except IndexError:
            cluster_id_str = "subproblem"
    
    file_name = f"solution_{cluster_id_str}.png" if cluster_id_str else "solution_merged.png"
    file_path = os.path.join(save_dir, file_name)
    plt.savefig(file_path, dpi=300)
    plt.close(fig) # Đóng figure để giải phóng bộ nhớ
    print(f"Solution visualization saved to {file_path}")

def plot_alns_history(run_history: Dict, op_history: Dict, save_dir: str):
    """
    Hàm chính để vẽ và lưu tất cả các biểu đồ phân tích về quá trình chạy ALNS.
    """
    if run_history and run_history['iteration']:
        print("  - Plotting convergence history...")
        _plot_convergence(run_history, save_dir=save_dir)
        
        print("  - Plotting acceptance criteria...")
        _plot_acceptance_criteria(run_history, save_dir=save_dir)
        
        print("  - Plotting destroy impact...")
        _plot_destroy_impact(run_history, save_dir=save_dir)
    else:
        print("  - Skipping ALNS run history plots (no data).")

    if op_history and op_history['iteration']:
        print("  - Plotting operator weights evolution...")
        _plot_operator_weights(op_history, save_dir=save_dir)
    else:
        print("  - Skipping operator history plots (no data).")
    
    # Đóng tất cả các figure đã được tạo để giải phóng bộ nhớ
    plt.close('all')