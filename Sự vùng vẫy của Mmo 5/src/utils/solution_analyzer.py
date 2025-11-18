# src/utils/solution_analyzer.py
from __future__ import annotations
from typing import TYPE_CHECKING
import sys
# Thêm dòng này:
from ..core.problem_parser import PickupCustomer 

if TYPE_CHECKING:
    from ..core.data_structures import Solution

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

# ==============================================================================
# HÀM NỘI BỘ (PRIVATE)
# ==============================================================================

def _calculate_and_print_extra_stats(solution: "Solution"):
    """
    Tính toán và in ra các chỉ số thống kê bổ sung về lời giải.
    (Lấy từ main_visualizer_tự_động.py)
    """
    fe_max_loads, se_max_loads, fe_parcels_counts, se_parcels_counts = [], [], [], []
    visited_satellites = set()
    for fe_route in solution.fe_routes:
        if fe_route.schedule: 
            fe_max_loads.append(max(event['load_after'] for event in fe_route.schedule))
        fe_parcels_counts.append(sum(len(se.get_customers()) for se in fe_route.serviced_se_routes))
        for se_route in fe_route.serviced_se_routes: 
            visited_satellites.add(se_route.satellite.id)
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

# ==============================================================================
# HÀM CÔNG KHAI (PUBLIC)
# ==============================================================================

def print_solution_details(solution: "Solution", execution_time: float):
    """
    In báo cáo chi tiết và đầy đủ của lời giải, bao gồm summary và chi tiết từng route.
    """
    print("\n" + "#"*70 + "\n### FINAL OPTIMAL SOLUTION ###\n" + "#"*70)
    print(f"Total execution time: {execution_time:.2f} seconds")
    
    print("\n" + "="*60 + "\n--- DETAILED SOLUTION REPORT ---\n" + "="*60)
    print(f"\n[SUMMARY]")
    
    # In các chỉ số chính
    print(f"Objective Cost (from config): {solution.get_objective_cost():.2f}")
    print(f"  -> Total Distance: {solution.calculate_total_cost():.2f}")
    total_travel_time = sum(r.total_travel_time for r in solution.fe_routes) + sum(r.total_travel_time for r in solution.se_routes)
    print(f"  -> Total Travel Time: {total_travel_time:.2f}")
    print(f"Number of FE Routes: {len(solution.fe_routes)}")
    print(f"Number of SE Routes: {len(solution.se_routes)}")
    print(f"Unserved Customers: {len(solution.unserved_customers)}")
    if solution.unserved_customers:
        print(f"  -> IDs: {[c.id for c in solution.unserved_customers]}")
    
    # Gọi hàm in thống kê bổ sung
    _calculate_and_print_extra_stats(solution)

    # --- IN CHI TIẾT CÁC TUYẾN ĐƯỜNG SE ---
    print("\n\n" + "-"*20 + " SECOND-ECHELON (SE) ROUTES " + "-"*20)
    if not solution.se_routes: 
        print("No SE routes in the solution.")
    else:
        # <<< BƯỚC 1: Khởi tạo biến đếm toàn cục >>>
        se_route_counter = 1
        
        # Nhóm các SE route theo FE route phục vụ chúng
        fe_to_se_map = {fe: [] for fe in solution.fe_routes}
        unassigned_se = []
        for se_route in solution.se_routes:
            assigned = False
            for fe_route in se_route.serving_fe_routes:
                if fe_route in fe_to_se_map:
                    fe_to_se_map[fe_route].append(se_route)
                    assigned = True
            if not assigned:
                unassigned_se.append(se_route)
        
        # In ra các SE route đã được nhóm
        for i, fe_route in enumerate(solution.fe_routes):
            print(f"\n--- SE Routes served by [FE Route #{i+1}] ---")
            se_routes_for_fe = sorted(fe_to_se_map.get(fe_route, []), key=lambda r: r.satellite.id)
            if not se_routes_for_fe:
                print("  (This FE route serves no SE routes)")
            for se_route in se_routes_for_fe:
                # <<< BƯỚC 2: Thêm tiêu đề đánh số trước khi in chi tiết >>>
                print(f"\n[SE Route #{se_route_counter}]") 
                print(se_route)
                se_route_counter += 1 # Tăng biến đếm

        # In ra các SE route không được gán (nếu có lỗi)
        if unassigned_se:
            print("\n--- Unassigned SE Routes (Potential Error) ---")
            for se_route in unassigned_se:
                # <<< BƯỚC 3: Đánh số cả các route không được gán >>>
                print(f"\n[SE Route #{se_route_counter}] (Unassigned)")
                print(se_route)
                se_route_counter += 1 # Tăng biến đếm

    # --- IN CHI TIẾT CÁC TUYẾN ĐƯỜNG FE ---
    print("\n\n" + "-"*20 + " FIRST-ECHELON (FE) ROUTES " + "-"*20)
    if not solution.fe_routes: 
        print("No FE routes in the solution.")
    else:
        for i, fe_route in enumerate(solution.fe_routes):
            print(f"\n[FE Route #{i+1}]")
            serviced_sats = sorted([se.satellite.id for se in fe_route.serviced_se_routes])
            print(f"Servicing Satellites: {serviced_sats if serviced_sats else 'None'}")
            print(fe_route) # Lệnh này sẽ gọi hàm __repr__ của lớp FERoute

def validate_solution_feasibility(solution: "Solution"):
    print("\n\n" + "="*60 + "\n--- ENHANCED SOLUTION FEASIBILITY VALIDATION ---\n" + "="*60)
    errors = []
    problem = solution.problem
    
    # ... (Copy toàn bộ code của hàm validate_solution_feasibility cũ vào đây) ...
    # Phần này bạn đã có và nó đã đúng
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
            load_after = event['load_after']
            if load_after < -1e-6 or load_after > problem.fe_vehicle_capacity + 1e-6: errors.append(f"FE Route #{i}: Capacity violation. Load: {load_after:.2f}, Capacity: {problem.fe_vehicle_capacity:.2f} after activity '{event['activity']}' at node {event['node_id']}")
        arrival_at_depot = fe_route.schedule[-1]['arrival_time']
        all_deadlines = {cust.deadline for se in fe_route.serviced_se_routes for cust in se.get_customers() if isinstance(cust, PickupCustomer)}
        if all_deadlines and arrival_at_depot > min(all_deadlines) + 1e-6: errors.append(f"FE Route #{i}: Violates effective deadline (Arrival: {arrival_at_depot:.2f} > Deadline: {min(all_deadlines):.2f})")
        for se_route in fe_route.serviced_se_routes:
            if fe_route not in se_route.serving_fe_routes: errors.append(f"FE Route #{i}: Link inconsistency. It serves SE (Sat {se_route.satellite.id}), but the SE route does not link back.")
    if not errors: print("\n[VALIDATION SUCCESS] Solution appears to be feasible and consistent.")
    else:
        print("\n[VALIDATION FAILED] Found the following potential issues:")
        for i, error in enumerate(errors): print(f"  {i+1}. {error}")
    print("="*60)