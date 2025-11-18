# File: run_clustered_solver.py (Phiên bản Hoàn chỉnh sau khi nâng cấp)

import time
import os
import sys
import shutil
import datetime
import random
import copy
import math
import pandas as pd
from typing import List

# --- Import từ cấu trúc src mới ---
from src import config
from src.core.problem_parser import ProblemInstance, Customer, Depot, Satellite, DeliveryCustomer, PickupCustomer
from src.core.data_structures import Solution
from src.algorithm.solution_generator import generate_initial_solution
from src.algorithm.lns_algorithm import run_alns_phase
from src.utils.logger import Logger
from src.utils.solution_analyzer import print_solution_details, validate_solution_feasibility
from src.utils.plotter import plot_solution_visualization, plot_customer_clusters # <--- IMPORT MỚI
from src.utils.solution_merger import merge_solutions
from src.algorithm.clustering.preprocessor import preprocess_and_add_effective_deadline
from src.algorithm.clustering.dissimilarity import create_dissimilarity_matrix
from src.algorithm.clustering.engine import analyze_k_and_suggest_optimal, run_clustering

# --- Import các toán tử ---
# (Toàn bộ khối import toán tử giữ nguyên như phiên bản trước)
from src.algorithm.lns.destroy_operators import (
    random_removal, shaw_removal, worst_slack_removal,
    worst_cost_removal, route_removal, satellite_removal,
    least_utilized_route_removal
)
from src.algorithm.lns.repair_operators import (
    greedy_repair, regret_insertion, earliest_deadline_first_insertion,
    farthest_first_insertion, largest_first_insertion, closest_first_insertion,
    earliest_time_window_insertion, latest_time_window_insertion,
    latest_deadline_first_insertion
)


# --- HÀM HELPER (ĐÃ VIẾT TRƯỚC ĐÓ) ---
def create_subproblem_instance(original_problem: ProblemInstance, customer_subset: List[Customer]) -> ProblemInstance:
    # (Hàm này giữ nguyên như phiên bản trước)
    sub_problem = copy.copy(original_problem)
    sub_problem.customers = customer_subset
    nodes_for_subproblem = [original_problem.depot] + original_problem.satellites + customer_subset
    sub_problem.node_objects = {node.id: node for node in nodes_for_subproblem}
    sub_problem.dist_matrix = {
        n1.id: {n2.id: math.sqrt((n1.x - n2.x)**2 + (n1.y - n2.y)**2) for n2 in nodes_for_subproblem}
        for n1 in nodes_for_subproblem
    }
    sub_problem._precompute_neighbors()
    return sub_problem

# --- HÀM HELPER MỚI ---
def export_subproblem_to_csv(sub_problem: ProblemInstance, cluster_id: int, save_dir: str):
    """Xuất dữ liệu của một bài toán con ra file CSV."""
    csv_dir = os.path.join(save_dir, "subproblems_csv")
    os.makedirs(csv_dir, exist_ok=True)
    
    data_list = []
    all_nodes = [sub_problem.depot] + sub_problem.satellites + sub_problem.customers
    
    for node in all_nodes:
        node_dict = {
            'ID': node.id, 'Type': -1, 'X': node.x, 'Y': node.y,
            'Demand': getattr(node, 'demand', 0), 'Service Time': node.service_time,
            'Early': getattr(node, 'ready_time', 0), 'Latest': getattr(node, 'due_time', 0),
            'Deadline': getattr(node, 'deadline', 0), 'FE Cap': sub_problem.fe_vehicle_capacity,
            'SE Cap': sub_problem.se_vehicle_capacity
        }
        if isinstance(node, Depot): node_dict['Type'] = 0
        elif isinstance(node, Satellite): node_dict['Type'] = 1
        elif isinstance(node, DeliveryCustomer): node_dict['Type'] = 2
        elif isinstance(node, PickupCustomer): node_dict['Type'] = 3
        data_list.append(node_dict)
        
    df = pd.DataFrame(data_list)
    column_order = ['ID', 'Type', 'X', 'Y', 'Demand', 'Service Time', 'Early', 'Latest', 'Deadline', 'FE Cap', 'SE Cap']
    df = df.reindex(columns=column_order)

    file_path = os.path.join(csv_dir, f"cluster_{cluster_id}_data.csv")
    df.to_csv(file_path, index=False)


def main():
    # --- 1. SETUP MÔI TRƯỜNG ---
    # (Giữ nguyên như phiên bản trước)
    if config.CLEAR_OLD_RESULTS_ON_START and os.path.exists(config.RESULTS_BASE_DIR):
        shutil.rmtree(config.RESULTS_BASE_DIR)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(config.RESULTS_BASE_DIR, f"clustered_run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    log_file_path = os.path.join(run_dir, "log.txt")
    sys.stdout = Logger(log_file_path, sys.stdout)
    sys.stderr = Logger(log_file_path, sys.stderr)
    shutil.copy('src/config.py', os.path.join(run_dir, 'config_snapshot.py'))
    start_time = time.time()
    random.seed(config.RANDOM_SEED)
    print("="*70 + "\nRUNNING CLUSTERED SOLVER\n" + "="*70)

    # --- 2. GIAI ĐOẠN PHÂN CỤM ---
    full_problem = ProblemInstance(file_path=config.FILE_PATH, vehicle_speed=config.VEHICLE_SPEED)
    preprocess_and_add_effective_deadline(full_problem)
    dissim_matrix = create_dissimilarity_matrix(full_problem)
    k_suggested, _ = analyze_k_and_suggest_optimal(dissim_matrix)
    
    try:
        user_input = input(f"\nEnter number of clusters (k) or press Enter to use suggested k={k_suggested}: ")
        k_final = int(user_input) if user_input.strip() else k_suggested
    except ValueError: k_final = k_suggested
    print(f"Using k = {k_final} for the final run.")
    
    labels = run_clustering(dissim_matrix, k_final)
    
    # === NÂNG CẤP: GỌI HÀM VẼ CỤM ===
    plot_customer_clusters(full_problem, labels, save_dir=run_dir)

    clusters = {i: [] for i in range(k_final)}
    for i, customer in enumerate(full_problem.customers):
        clusters[labels[i]].append(customer)

    # --- 3. GIAI ĐOẠN GIẢI QUYẾT TỪNG CỤM ---
    sub_solutions = []
    destroy_operators_map = { "random_removal": random_removal, "worst_slack_removal": worst_slack_removal, "worst_cost_removal": worst_cost_removal, "route_removal": route_removal, "satellite_removal": satellite_removal, "least_utilized_route_removal": least_utilized_route_removal }
    repair_operators_map = { "greedy_repair": greedy_repair, "earliest_deadline_first_insertion": earliest_deadline_first_insertion, "farthest_first_insertion": farthest_first_insertion, "largest_first_insertion": largest_first_insertion, "closest_first_insertion": closest_first_insertion, "earliest_time_window_insertion": earliest_time_window_insertion, "latest_time_window_insertion": latest_time_window_insertion, "latest_deadline_first_insertion": latest_deadline_first_insertion }
    
    # === NÂNG CẤP: TẠO THƯ MỤC LƯU PLOT CỦA TỪNG CỤM ===
    sub_solutions_plots_dir = os.path.join(run_dir, "subproblem_solutions")
    os.makedirs(sub_solutions_plots_dir, exist_ok=True)

    for cluster_id, customer_list in clusters.items():
        if not customer_list: continue
            
        print("\n" + "="*60 + f"\nSOLVING SUB-PROBLEM FOR CLUSTER {cluster_id} ({len(customer_list)} customers)\n" + "="*60)
        sub_problem = create_subproblem_instance(full_problem, customer_list)
        
        # === NÂNG CẤP: XUẤT FILE CSV CHO BÀI TOÁN CON ===
        export_subproblem_to_csv(sub_problem, cluster_id, save_dir=run_dir)
        
        initial_state = generate_initial_solution(sub_problem, lns_iterations=config.LNS_INITIAL_ITERATIONS, q_percentage=config.Q_PERCENTAGE_INITIAL)
        best_state, (_, _) = run_alns_phase(initial_state=initial_state, iterations=config.ALNS_MAIN_ITERATIONS, destroy_operators=destroy_operators_map, repair_operators=repair_operators_map)
        
        sub_solution = best_state.solution
        
        # === NÂNG CẤP: TẠO TIÊU ĐỀ VÀ VẼ LỜI GIẢI CỦA CỤM ===
        sub_solution.custom_title = f"Solution for Cluster {cluster_id} (Cost: {sub_solution.get_objective_cost():.2f})"
        plot_solution_visualization(sub_solution, save_dir=sub_solutions_plots_dir)
        
        print(f"--- Finished solving for cluster {cluster_id}. Sub-problem cost: {best_state.cost:.2f} ---")
        sub_solutions.append(sub_solution)

    # --- 4. GIAI ĐOẠN HỢP NHẤT VÀ BÁO CÁO ---
    merged_solution = merge_solutions(sub_solutions, full_problem)
    end_time = time.time()

    print("\n" + "="*70 + "\nEVALUATING FINAL MERGED SOLUTION\n" + "="*70)
    print_solution_details(merged_solution, execution_time=end_time - start_time)
    validate_solution_feasibility(merged_solution)
    
    # === NÂNG CẤP: VẼ LỜI GIẢI TỔNG THỂ ===
    plot_solution_visualization(merged_solution, save_dir=run_dir)
    
    print(f"\nClustered run complete. All artifacts saved to: {run_dir}")

if __name__ == "__main__":
    main()