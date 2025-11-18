# run_baseline_solver.py

import time
import os
import sys
import shutil
import datetime
import random
import matplotlib.pyplot as plt

# --- Import từ cấu trúc src mới ---
from src import config
from src.core.problem_parser import ProblemInstance
from src.algorithm.solution_generator import generate_initial_solution
from src.algorithm.lns_algorithm import run_alns_phase
from src.utils.logger import Logger
from src.utils.solution_analyzer import print_solution_details, validate_solution_feasibility
from src.utils.plotter import plot_solution_visualization, plot_alns_history

# --- Import đầy đủ các toán tử ---
from src.algorithm.lns.destroy_operators import (
    random_removal, 
    shaw_removal, 
    worst_slack_removal,
    worst_cost_removal,
    route_removal,
    satellite_removal,
    least_utilized_route_removal 
)
from src.algorithm.lns.repair_operators import (
    greedy_repair, 
    regret_insertion, 
    earliest_deadline_first_insertion,
    farthest_first_insertion,
    largest_first_insertion,
    closest_first_insertion,        
    earliest_time_window_insertion, 
    latest_time_window_insertion,   
    latest_deadline_first_insertion 
)


def main():
    """
    Hàm chính để chạy bộ giải ALNS trên toàn bộ bài toán (kịch bản baseline).
    """
    
    # --- 1. SETUP MÔI TRƯỜỜNG ---
    # Dọn dẹp kết quả cũ nếu được cấu hình
    if config.CLEAR_OLD_RESULTS_ON_START and os.path.exists(config.RESULTS_BASE_DIR):
        print(f"Config 'CLEAR_OLD_RESULTS_ON_START' is True. Removing old '{config.RESULTS_BASE_DIR}' directory...")
        shutil.rmtree(config.RESULTS_BASE_DIR)
    
    # Tạo thư mục chạy cho lần này
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(config.RESULTS_BASE_DIR, f"baseline_run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    
    # Thiết lập logger để ghi lại toàn bộ output
    log_file_path = os.path.join(run_dir, "log.txt")
    sys.stdout = Logger(log_file_path, sys.stdout)
    sys.stderr = Logger(log_file_path, sys.stderr)

    # Sao chép file config để lưu lại cấu hình đã chạy
    try:
        shutil.copy('src/config.py', os.path.join(run_dir, 'config_snapshot.py'))
    except FileNotFoundError:
        print("Warning: Could not find 'src/config.py' to create a snapshot.")

    start_time = time.time()
    random.seed(config.RANDOM_SEED)

    # In thông tin cấu hình ban đầu
    print("="*80)
    print("INITIALIZING BASELINE SOLVER (WITHOUT CLUSTERING)")
    print(f"Run ID: baseline_run_{timestamp}")
    print(f"Results for this run will be saved in: {run_dir}")
    print("="*80)
    
    # --- 2. KHỞI TẠO VÀ CHẠY ALNS ---
    try:
        problem = ProblemInstance(file_path=config.FILE_PATH, vehicle_speed=config.VEHICLE_SPEED)
    except (FileNotFoundError, Exception) as e:
        print(f"FATAL ERROR: Could not load data file at '{config.FILE_PATH}'.")
        print(f"Details: {e}")
        return

    # Định nghĩa các toán tử destroy và repair sẽ được sử dụng
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

    # --- Chạy thuật toán ---
    # Giai đoạn 1: Tạo lời giải ban đầu
    print("\n" + "#"*70 + "\n### STAGE 1: GENERATING INITIAL SOLUTION ###\n" + "#"*70)
    initial_state = generate_initial_solution(
        problem, 
        lns_iterations=config.LNS_INITIAL_ITERATIONS, 
        q_percentage=config.Q_PERCENTAGE_INITIAL
    )
    
    # Giai đoạn 2: Chạy ALNS
    print("\n" + "#"*70 + "\n### STAGE 2: ADAPTIVE LARGE NEIGHBORHOOD SEARCH ###\n" + "#"*70)
    best_state, (run_history, op_history) = run_alns_phase(
        initial_state=initial_state,
        iterations=config.ALNS_MAIN_ITERATIONS,
        destroy_operators=destroy_operators_map,
        repair_operators=repair_operators_map
    )
    
    end_time = time.time()
    final_solution = best_state.solution

    # --- 3. BÁO CÁO VÀ PHÂN TÍCH KẾT QUẢ ---
    # In báo cáo chi tiết ra console và file log
    print_solution_details(final_solution, execution_time=end_time - start_time)
    
    # Kiểm tra tính khả thi của lời giải cuối cùng
    validate_solution_feasibility(final_solution)
    
    # Vẽ và lưu tất cả các biểu đồ
    print("\nGenerating and saving plots...")
    plot_solution_visualization(final_solution, save_dir=run_dir)
    plot_alns_history(run_history, op_history, save_dir=run_dir)
    
    print(f"\nBaseline run complete. All artifacts have been saved to: {run_dir}")
    # Bỏ comment dòng dưới nếu bạn muốn các biểu đồ tự động hiện lên sau khi chạy xong
    # plt.show()

if __name__ == "__main__":
    main()