# src/clustering/dissimilarity.py
from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np
import time

# Sử dụng relative import
from src import config

if TYPE_CHECKING:
    from core.problem_parser import ProblemInstance, Customer

def _calculate_std_pdd_for_pair(customer_i: "Customer", customer_j: "Customer", problem: "ProblemInstance") -> float:
    """
    Ham noi bo de tinh gia tri khac biet STD-PDD cho mot cap khach hang.
    """
    # ... (phần spatial_component và temporal_penalty giữ nguyên) ...
    coords_i = (customer_i.x, customer_i.y)
    coords_j = (customer_j.x, customer_j.y)

    # --- 1. Thanh phan Khong gian (Spatial) ---
    spatial_component = problem.get_distance(customer_i.id, customer_j.id)

    # --- 2. Thanh phan Thoi gian (Temporal) ---
    travel_time_ij = problem.get_travel_time(customer_i.id, customer_j.id)
    f_ij = customer_j.effective_latest - (customer_i.ready_time + customer_i.service_time + travel_time_ij)
    h_ij = max(0, customer_j.ready_time - (customer_i.effective_latest + customer_i.service_time + travel_time_ij))
    
    # MAX_SCHEDULING_FLEXIBILITY vẫn có thể giữ ở config vì nó là một hằng số heuristic
    temporal_penalty = (f_ij - h_ij) / config.MAX_SCHEDULING_FLEXIBILITY
    
    # --- 3. Thanh phan Nhu cau (Demand) ---
    # THAY ĐỔI Ở ĐÂY: Lấy se_vehicle_capacity từ đối tượng 'problem'
    if problem.se_vehicle_capacity > 0:
        demand_penalty = (abs(customer_i.demand) + abs(customer_j.demand)) / problem.se_vehicle_capacity
    else:
        demand_penalty = float('inf') # Tránh lỗi chia cho 0
        
    # --- Ket hop ---
    dissimilarity = spatial_component * (2 - temporal_penalty + demand_penalty)
    
    return dissimilarity


def create_dissimilarity_matrix(problem: "ProblemInstance") -> np.ndarray:
    """
    Tao ma tran khac biet NxN cho tat ca cac khach hang.
    
    Args:
        problem (ProblemInstance): Đối tượng bài toán chứa danh sách khách hàng đã được tiền xử lý.

    Returns:
        np.ndarray: Ma tran khac biet doi xung.
    """
    print("\n--- Calculating dissimilarity matrix...")
    start_time = time.time()
    
    customers_list = problem.customers
    num_customers = len(customers_list)
    dissimilarity_matrix = np.zeros((num_customers, num_customers))

    for i in range(num_customers):
        for j in range(i, num_customers):
            if i == j:
                continue
            
            customer_i = customers_list[i]
            customer_j = customers_list[j]

            std_ij = _calculate_std_pdd_for_pair(customer_i, customer_j, problem)
            std_ji = _calculate_std_pdd_for_pair(customer_j, customer_i, problem)
            
            value = min(std_ij, std_ji)
            dissimilarity_matrix[i, j] = value
            dissimilarity_matrix[j, i] = value
    
    end_time = time.time()
    print(f"Dissimilarity matrix calculation completed in {end_time - start_time:.2f} seconds.")
    
    return dissimilarity_matrix