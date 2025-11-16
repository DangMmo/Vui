# --- START OF FILE main_visualizer.py ---

import random
import config
import time
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


# <<< HÀM MỚI ĐỂ TÍNH TOÁN CÁC CHỈ SỐ BỔ SUNG >>>
def calculate_and_print_extra_stats(solution: Solution):
    """
    Tính toán và in ra các chỉ số thống kê bổ sung về lời giải.
    """
    # --- 1. Khởi tạo các biến ---
    fe_max_loads = []
    se_max_loads = []
    fe_parcels_counts = []
    se_parcels_counts = []
    visited_satellites = set()

    # --- 2. Lặp qua các route để thu thập dữ liệu ---
    for fe_route in solution.fe_routes:
        # Tải trọng tối đa của FE route
        if fe_route.schedule:
            max_load = max(event['load_after'] for event in fe_route.schedule)
            fe_max_loads.append(max_load)
        
        # Số lượng "bưu kiện" (khách hàng) mà FE route này phục vụ
        parcels_on_this_fe = sum(len(se.get_customers()) for se in fe_route.serviced_se_routes)
        fe_parcels_counts.append(parcels_on_this_fe)

        # Các vệ tinh được FE route này ghé thăm
        for se_route in fe_route.serviced_se_routes:
            visited_satellites.add(se_route.satellite.id)

    for se_route in solution.se_routes:
        # Tải trọng tối đa của SE route là tổng tải cần giao
        se_max_loads.append(se_route.total_load_delivery)
        # Số lượng khách hàng SE route này phục vụ
        se_parcels_counts.append(len(se_route.get_customers()))

    # --- 3. Tính toán giá trị trung bình (tránh lỗi chia cho 0) ---
    avg_fe_max_load = sum(fe_max_loads) / len(fe_max_loads) if fe_max_loads else 0
    avg_se_max_load = sum(se_max_loads) / len(se_max_loads) if se_max_loads else 0
    avg_fe_parcels = sum(fe_parcels_counts) / len(fe_parcels_counts) if fe_parcels_counts else 0
    avg_se_parcels = sum(se_parcels_counts) / len(se_parcels_counts) if se_parcels_counts else 0
    num_visited_satellites = len(visited_satellites)

    # --- 4. In kết quả theo định dạng yêu cầu ---
    print("\n[ADDITIONAL STATISTICS]")
    header = f"{'Avg FE Max Load':<20} {'Avg SE Max Load':<20} {'Avg FE Parcels':<20} {'Avg SE Parcels':<20} {'#Satellite Visited':<20}"
    line = "-" * len(header)
    values = f"{avg_fe_max_load:<20.2f} {avg_se_max_load:<20.2f} {avg_fe_parcels:<20.2f} {avg_se_parcels:<20.2f} {num_visited_satellites:<20}"
    
    print(line)
    print(header)
    print(line)
    print(values)
    print(line)


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
    
    # <<< GỌI HÀM MỚI TẠI ĐÂY >>>
    calculate_and_print_extra_stats(solution)

    print("\n\n" + "-"*20 + " SECOND-ECHELON (SE) ROUTES " + "-"*20)
    if not solution.se_routes: 
        print("No SE routes in the solution.")
    else:
        fe_to_se_map = {fe: [] for fe in solution.fe_routes}
        unassigned_se = []
        for se_route in solution.se_routes:
            assigned = False
            for fe_route in se_route.serving_fe_routes:
                if fe_route in fe_to_se_map: fe_to_se_map[fe_route].append(se_route); assigned = True
            if not assigned: unassigned_se.append(se_route)
        for i, fe_route in enumerate(solution.fe_routes):
            print(f"\n--- SE Routes served by [FE Route #{i+1}] ---")
            se_routes_for_fe = sorted(fe_to_se_map.get(fe_route, []), key=lambda r: r.satellite.id)
            if not se_routes_for_fe: print("  (This FE route serves no SE routes)")
            for se_route in se_routes_for_fe: print(se_route)
        if unassigned_se:
            print("\n--- Unassigned SE Routes (Potential Error) ---")
            for se_route in unassigned_se: print(se_route)
    print("\n\n" + "-"*20 + " FIRST-ECHELON (FE) ROUTES " + "-"*20)
    if not solution.fe_routes: 
        print("No FE routes in the solution.")
    else:
        for i, fe_route in enumerate(solution.fe_routes):
            print(f"\n[FE Route #{i+1}]")
            serviced_sats = sorted([se.satellite.id for se in fe_route.serviced_se_routes])
            print(f"Servicing Satellites: {serviced_sats if serviced_sats else 'None'}")
            print(fe_route)

def validate_solution_feasibility(solution: Solution):
    print("\n\n" + "="*60 + "\n--- ENHANCED SOLUTION FEASIBILITY VALIDATION ---\n" + "="*60)
    errors = []; problem = solution.problem
    all_served_ids = set(solution.customer_to_se_route_map.keys())
    all_problem_ids = {c.id for c in problem.customers}
    total_customers_in_routes = sum(len(r.get_customers()) for r in solution.se_routes)
    if len(all_served_ids) != total_customers_in_routes: errors.append(f"MISMATCH: customer_map ({len(all_served_ids)}) vs. customers_in_routes ({total_customers_in_routes})")
    if len(all_served_ids) + len(solution.unserved_customers) != len(all_problem_ids): errors.append(f"MISMATCH: Served ({len(all_served_ids)}) + Unserved ({len(solution.unserved_customers)}) != Total ({len(all_problem_ids)})")
    for i, se_route in enumerate(solution.se_routes):
        current_load = se_route.total_load_delivery
        if current_load > problem.se_vehicle_capacity + 1e-6: errors.append(f"SE Route #{i} (Sat {se_route.satellite.id}): Initial delivery load ({current_load:.2f}) exceeds capacity ({problem.se_vehicle_capacity:.2f})")
        for cust_id in se_route.nodes_id[1:-1]:
            cust = problem.node_objects[cust_id]
            if cust.type == 'DeliveryCustomer': current_load -= cust.demand
            else: current_load += cust.demand
            if current_load < -1e-6 or current_load > problem.se_vehicle_capacity + 1e-6: errors.append(f"SE Route #{i} (Sat {se_route.satellite.id}): Load violation at customer {cust.id}. Load: {current_load:.2f}, Capacity: {problem.se_vehicle_capacity:.2f}")
        for cust in se_route.get_customers():
            start_time = se_route.service_start_times.get(cust.id)
            if start_time is None: errors.append(f"SE Route #{i} (Sat {se_route.satellite.id}): Customer {cust.id} is in route but has no start time."); continue
            if start_time < cust.ready_time - 1e-6: errors.append(f"SE Route #{i} (Sat {se_route.satellite.id}): Customer {cust.id} served too early (Start: {start_time:.2f} < Ready: {cust.ready_time:.2f})")
            if start_time > cust.due_time + 1e-6: errors.append(f"SE Route #{i} (Sat {se_route.satellite.id}): Customer {cust.id} served too late (Start: {start_time:.2f} > Due: {cust.due_time:.2f})")
        if not se_route.serving_fe_routes: errors.append(f"SE Route #{i} (Sat {se_route.satellite.id}): Is not served by any FE route.")
    for i, fe_route in enumerate(solution.fe_routes):
        if not fe_route.schedule and fe_route.serviced_se_routes: errors.append(f"FE Route #{i}: Has no schedule but services {len(fe_route.serviced_se_routes)} SE routes."); continue
        if not fe_route.schedule: continue
        for event in fe_route.schedule:
            if event['load_after'] < -1e-6 or event['load_after'] > problem.fe_vehicle_capacity + 1e-6: errors.append(f"FE Route #{i}: Capacity violation...")
        arrival_at_depot = fe_route.schedule[-1]['arrival_time']
        all_deadlines = {cust.deadline for se in fe_route.serviced_se_routes for cust in se.get_customers() if isinstance(cust, PickupCustomer)}
        if all_deadlines and arrival_at_depot > min(all_deadlines) + 1e-6: errors.append(f"FE Route #{i}: Violates effective deadline...")
        for se_route in fe_route.serviced_se_routes:
            if fe_route not in se_route.serving_fe_routes: errors.append(f"FE Route #{i}: Link inconsistency...")
    if not errors: print("\n[VALIDATION SUCCESS] Solution appears to be feasible and consistent.")
    else:
        print("\n[VALIDATION FAILED] Found the following potential issues:")
        for i, error in enumerate(errors): print(f"  {i+1}. {error}")
    print("="*60)

def main():
    start_time = time.time()
    random.seed(config.RANDOM_SEED)
    print("="*70); print("Starting ALNS Solver with the following objective configuration:")
    print(f"  - Primary Objective: {config.PRIMARY_OBJECTIVE}"); print(f"  - Optimize Vehicle Count: {config.OPTIMIZE_VEHICLE_COUNT}")
    if config.OPTIMIZE_VEHICLE_COUNT: print(f"  - FE Vehicle Weight: {config.WEIGHT_FE_VEHICLE}\n  - SE Vehicle Weight: {config.WEIGHT_SE_VEHICLE}")
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
    validate_solution_feasibility(final_solution)
    
    if final_solution:
        print("\nDisplaying solution visualization...")
        visualize_solution(final_solution)

    print("\nDisplaying algorithm performance analytics... (Close all plot windows to exit)")
    if run_history and run_history['iteration']:
        analytics_plots.plot_convergence(run_history)
        analytics_plots.plot_acceptance_criteria(run_history)
        analytics_plots.plot_destroy_impact(run_history)
    if op_history and op_history['iteration']:
        analytics_plots.plot_operator_weights(op_history)
    
    plt.show()

if __name__ == "__main__":
    main()

# --- END OF FILE main_visualizer.py ---