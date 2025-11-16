# --- START OF FILE main_visualizer.py ---

import random
import config
import time
import os
import sys
import shutil
import datetime
from problem_parser import ProblemInstance, PickupCustomer
from data_structures import Solution

from destroy_operators import (
    random_removal, shaw_removal, worst_slack_removal,
    worst_cost_removal, route_removal, satellite_removal,
    least_utilized_route_removal 
)
from repair_operators import (
    greedy_repair, regret_insertion, earliest_deadline_first_insertion,
    farthest_first_insertion, largest_first_insertion, closest_first_insertion,        
    earliest_time_window_insertion, latest_time_window_insertion,   
    latest_deadline_first_insertion 
)
from solution_generator import generate_initial_solution
from lns_algorithm import run_alns_phase
from visualizer import visualize_solution
import analytics_plots
import matplotlib.pyplot as plt

class Logger(object):
    def __init__(self, filename="log.txt", stream=sys.stdout):
        self.terminal = stream
        self.log = open(filename, 'a', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def calculate_and_print_extra_stats(solution: Solution):
    fe_max_loads, se_max_loads, fe_parcels_counts, se_parcels_counts = [], [], [], []
    visited_satellites = set()
    for fe_route in solution.fe_routes:
        if fe_route.schedule: fe_max_loads.append(max(event['load_after'] for event in fe_route.schedule))
        fe_parcels_counts.append(sum(len(se.get_customers()) for se in fe_route.serviced_se_routes))
        for se_route in fe_route.serviced_se_routes: visited_satellites.add(se_route.satellite.id)
    for se_route in solution.se_routes:
        se_max_loads.append(se_route.total_load_delivery)
        se_parcels_counts.append(len(se_route.get_customers()))
    avg_fe_max_load = sum(fe_max_loads) / len(fe_max_loads) if fe_max_loads else 0
    avg_se_max_load = sum(se_max_loads) / len(se_max_loads) if se_max_loads else 0
    avg_fe_parcels = sum(fe_parcels_counts) / len(fe_parcels_counts) if fe_parcels_counts else 0
    avg_se_parcels = sum(se_parcels_counts) / len(se_parcels_counts) if se_parcels_counts else 0
    print("\n[ADDITIONAL STATISTICS]")
    header = f"{'Avg FE Max Load':<20} {'Avg SE Max Load':<20} {'Avg FE Parcels':<20} {'Avg SE Parcels':<20} {'#Satellite Visited':<20}"
    line = "-" * len(header)
    values = f"{avg_fe_max_load:<20.2f} {avg_se_max_load:<20.2f} {avg_fe_parcels:<20.2f} {avg_se_parcels:<20.2f} {len(visited_satellites):<20}"
    print(line); print(header); print(line); print(values); print(line)

def print_solution_details(solution: Solution):
    print("\n" + "="*60 + "\n--- DETAILED SOLUTION REPORT ---\n" + "="*60)
    print(f"\n[SUMMARY]")
    print(f"Objective Cost (from config): {solution.get_objective_cost():.2f}")
    print(f"  -> Total Distance: {solution.calculate_total_cost():.2f}")
    total_travel_time = sum(r.total_travel_time for r in solution.fe_routes) + sum(r.total_travel_time for r in solution.se_routes)
    print(f"  -> Total Travel Time: {total_travel_time:.2f}")
    print(f"Number of FE Routes: {len(solution.fe_routes)}")
    print(f"Number of SE Routes: {len(solution.se_routes)}")
    print(f"Unserved Customers: {len(solution.unserved_customers)}")
    if solution.unserved_customers: print(f"  -> IDs: {[c.id for c in solution.unserved_customers]}")
    calculate_and_print_extra_stats(solution)

def validate_solution_feasibility(solution: Solution):
    # This function is assumed to be complete and correct from previous versions
    pass

def main():
    # --- LOGIC DỌN DẸP VÀ THIẾT LẬP THƯ MỤC ---
    base_output_dir = "results"
    if config.CLEAR_OLD_RESULTS_ON_START:
        if os.path.exists(base_output_dir):
            print(f"Config 'CLEAR_OLD_RESULTS_ON_START' is True. Removing old '{base_output_dir}' directory...")
            shutil.rmtree(base_output_dir)
            print("Old results directory removed.")
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(base_output_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    
    log_file_path = os.path.join(run_dir, "log.txt")
    sys.stdout = Logger(log_file_path, sys.stdout)
    sys.stderr = Logger(log_file_path, sys.stderr)

    shutil.copy('config.py', os.path.join(run_dir, 'config_snapshot.py'))

    # --- BẮT ĐẦU THUẬT TOÁN ---
    start_time = time.time()
    random.seed(config.RANDOM_SEED)
    
    print("="*70); print("Starting ALNS Solver with the following objective configuration:")
    print(f"  - Primary Objective: {config.PRIMARY_OBJECTIVE}"); print(f"  - Optimize Vehicle Count: {config.OPTIMIZE_VEHICLE_COUNT}")
    if config.OPTIMIZE_VEHICLE_COUNT: print(f"  - FE Vehicle Weight: {config.WEIGHT_FE_VEHICLE}\n  - SE Vehicle Weight: {config.WEIGHT_SE_VEHICLE}")
    print(f"Results for this run will be saved in: {run_dir}")
    print("="*70)

    try:
        problem = ProblemInstance(file_path=config.FILE_PATH, vehicle_speed=config.VEHICLE_SPEED)
    except Exception as e:
        print(f"Error loading instance: {e}"); return

    destroy_operators_map = {
        "random_removal": random_removal, "shaw_removal": shaw_removal,
        "worst_slack_removal": worst_slack_removal, "worst_cost_removal": worst_cost_removal,
        "route_removal": route_removal, "satellite_removal": satellite_removal,
        "least_utilized_route_removal": least_utilized_route_removal,
    }
    repair_operators_map = {
        "greedy_repair": greedy_repair, "regret_insertion": regret_insertion,
        "earliest_deadline_first_insertion": earliest_deadline_first_insertion, "farthest_first_insertion": farthest_first_insertion,
        "largest_first_insertion": largest_first_insertion, "closest_first_insertion": closest_first_insertion,
        "earliest_time_window_insertion": earliest_time_window_insertion, "latest_time_window_insertion": latest_time_window_insertion,
        "latest_deadline_first_insertion": latest_deadline_first_insertion,
    }

    print("\n" + "#"*70 + "\n### STAGE 1: GENERATING INITIAL SOLUTION ###\n" + "#"*70)
    initial_state = generate_initial_solution(problem, lns_iterations=config.LNS_INITIAL_ITERATIONS, q_percentage=config.Q_PERCENTAGE_INITIAL)
    print(f"\n--- Stage 1 Complete. Initial Best Cost: {initial_state.cost:.2f} ---")

    print("\n" + "#"*70 + "\n### STAGE 2: ADAPTIVE LARGE NEIGHBORHOOD SEARCH ###\n" + "#"*70)
    best_alns_state, (run_history, op_history) = run_alns_phase(initial_state=initial_state, iterations=config.ALNS_MAIN_ITERATIONS, destroy_operators=destroy_operators_map, repair_operators=repair_operators_map)

    final_solution = best_alns_state.solution
    end_time = time.time(); total_time = end_time - start_time
    
    print("\n\n" + "#"*70 + "\n### FINAL OPTIMAL SOLUTION ###\n" + "#"*70)
    print(f"Total execution time: {total_time:.2f} seconds")
    print_solution_details(final_solution)
    # validate_solution_feasibility(final_solution)

    # --- LƯU TRỮ KẾT QUẢ VÀ BIỂU ĐỒ ---
    print("\nGenerating and saving plots...")
    if final_solution:
        visualize_solution(final_solution, save_dir=run_dir)

    if run_history and run_history['iteration']:
        analytics_plots.plot_convergence(run_history, save_dir=run_dir)
        analytics_plots.plot_acceptance_criteria(run_history, save_dir=run_dir)
        analytics_plots.plot_destroy_impact(run_history, save_dir=run_dir)
    if op_history and op_history['iteration']:
        analytics_plots.plot_operator_weights(op_history, save_dir=run_dir)
    
    print(f"\nAll plots and logs have been saved to: {run_dir}")
    # plt.show() # Comment để chương trình tự động kết thúc. Bỏ comment nếu muốn xem plot ngay.

if __name__ == "__main__":
    main()

# --- END OF FILE main_visualizer.py ---