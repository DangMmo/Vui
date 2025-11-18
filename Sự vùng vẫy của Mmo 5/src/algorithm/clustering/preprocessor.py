# src/clustering/preprocessor.py
from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np

# Sử dụng relative import
from src import config

if TYPE_CHECKING:
    from core.problem_parser import ProblemInstance, Customer, Satellite

def preprocess_and_add_effective_deadline(problem: "ProblemInstance"):
    """
    Tien xu ly du lieu khach hang de tinh toan 'cua so thoi gian hieu dung'.

    Thao tác trực tiếp trên các đối tượng Customer trong problem.customers để thêm
    thuộc tính 'effective_latest'.
    
    Args:
        problem (ProblemInstance): Đối tượng bài toán chứa toàn bộ dữ liệu.
    """
    print("\n--- Preprocessing customers for clustering (calculating effective deadlines)...")
    
    hub = problem.depot
    satellites = problem.satellites
    
    pickup_customer_count = 0
    for customer in problem.customers:
        # 1. Khởi tạo giá trị ban đầu cho tất cả khách hàng
        # Sử dụng due_time là giá trị mặc định cho latest time window
        customer.effective_latest = customer.due_time
        
        # 2. Chỉ xử lý cho các khách hàng lấy hàng (PickupCustomer)
        if customer.type == 'PickupCustomer':
            pickup_customer_count += 1
            customer_coords = (customer.x, customer.y)
            
            # --- Tìm vệ tinh gần nhất với khách hàng ---
            nearest_satellite = min(
                satellites, 
                key=lambda sat: problem.get_distance(customer.id, sat.id)
            )
            
            if nearest_satellite is None:
                continue

            # --- Tính toán ngược thời gian từ deadline tại Hub ---
            # Sử dụng các hàm get_travel_time đã được tối ưu hóa của ProblemInstance
            time_sat_to_hub = problem.get_travel_time(nearest_satellite.id, hub.id)
            latest_departure_from_sat = customer.deadline - time_sat_to_hub
            latest_arrival_at_sat = latest_departure_from_sat # Giả định service time của satellite cho FE là 0
            
            time_cust_to_sat = problem.get_travel_time(customer.id, nearest_satellite.id)
            latest_departure_from_customer = latest_arrival_at_sat - time_cust_to_sat
            latest_effective_arrival = latest_departure_from_customer - customer.service_time
            
            # --- Cập nhật giá trị 'effective_latest' ---
            # Lấy giá trị nhỏ hơn giữa deadline gốc tại khách hàng và deadline hieu dung vua tinh
            final_latest = min(customer.due_time, latest_effective_arrival)
            customer.effective_latest = final_latest
    
    print(f"Found and processed {pickup_customer_count} pickup customers.")
    print("Preprocessing complete.")