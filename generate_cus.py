# cus.py - Script sinh dữ liệu cho bài toán 2E-VRP-PDD
# Phiên bản nâng cấp: Tích hợp chuyển đổi tọa độ WGS84 sang UTM bằng mã EPSG.

# --- BƯỚC 1: IMPORT CÁC THƯ VIỆN CẦN THIẾT ---
import pandas as pd
import numpy as np
import random
import os
import argparse
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Import thư viện chuyển đổi tọa độ và thiết lập đường dẫn dữ liệu
import pyproj
from pyproj import CRS, Transformer # <<< THAY ĐỔI Ở ĐÂY
import os
import site

# ==============================================================================
# BƯỚC 2: CẤU HÌNH HỆ THỐNG (CONFIGURATION)
# ==============================================================================

# Các tham số mặc định toàn cục
GLOBAL_PARAMS = {
    "default_input_file": "Case khu 10A.csv",
    "default_output_filename_wgs84": "Generated_Instance_WGS84.csv", # File với tọa độ gốc (kinh độ, vĩ độ)
    "default_output_filename_utm": "Generated_Instance_UTM.csv",     # File với tọa độ UTM (mét)
    "plot_filename_wgs84": "Instance_Visualization_WGS84.png",
    "plot_filename_utm": "Instance_Visualization_UTM.png",                 # Tên file hình ảnh trực quan hóa
    "distribution_radius_km": 2.5,                                   # Bán kính phân bố khách hàng quanh vệ tinh (km)
    "satellite_service_time": 15,                                    # Thời gian phục vụ tại mỗi vệ tinh (phút)
    
    # MÃ EPSG: Cách hiện đại và đáng tin cậy để định nghĩa hệ tọa độ.
    # EPSG:32648 là mã cho UTM Zone 48N, bao phủ khu vực miền Nam Việt Nam.
    # Nếu dữ liệu ở miền Bắc (vd: Hà Nội), sử dụng mã 32647 (UTM Zone 47N).
    "utm_epsg_code": 32648 
}
# ------------------------------------------------------------------------------
# QUY ĐỔI THỜI GIAN (TIME REFERENCE: T=0 -> 07:00 AM)
# ------------------------------------------------------------------------------
CUSTOMER_PROFILES = {
    # 1. Dân cư: 15%, 0-660 (7h-18h)
    "RESIDENTIAL": {
        "ratio": 0.15,
        "demand_range": (1, 5),    # Hộ gia đình mua lẻ
        "distribution": "uniform",
        "time_windows": [(0, 660)],
        "service_time": 5,
        "pickup_ratio": 0.2,       # Ít khi gửi hàng
        "deadline_opts": [720, 840] # Cuối ngày
    },

    # 2. Khu công nghiệp: 15%, 0-240 (7h-11h)
    "INDUSTRIAL": {
        "ratio": 0.15,
        "demand_range": (30, 60),  # Nhu cầu rất lớn
        "distribution": "normal",
        "time_windows": [(0, 240)],
        "service_time": 15,        # Thời gian bốc hàng lâu
        "pickup_ratio": 0.6,       # Tỷ lệ gửi hàng đi cao (Thành phẩm)
        "deadline_opts": [420, 540] # Cần đi sớm (14h, 16h)
    },

    # 3. Trường học: 15%, 240-360 (11h-13h) - Giờ trưa
    "SCHOOL": {
        "ratio": 0.15,
        "demand_range": (10, 25),  # Suất ăn/VPP
        "distribution": "normal",
        "time_windows": [(240, 360)],
        "service_time": 10,
        "pickup_ratio": 0.1,
        "deadline_opts": [420]     # Gấp
    },

    # 4. Doanh nghiệp: 15%, 360-660 (13h-18h)
    "ENTERPRISE": {
        "ratio": 0.15,
        "demand_range": (5, 15),   # Văn phòng phẩm/Hồ sơ
        "distribution": "uniform",
        "time_windows": [(360, 660)],
        "service_time": 8,
        "pickup_ratio": 0.4,       # Gửi thư từ/hàng mẫu
        "deadline_opts": [780]     # 20:00 (về Hub xử lý đêm)
    },

    # --- NHÓM KHÓ TÍNH (STRICT) - Chia nhỏ theo khung giờ ---
    
    # 5. Khó tính 1: 10%, 180-420 (10h-14h)
    "STRICT_MIDDAY": {
        "ratio": 0.10,
        "demand_range": (5, 12),
        "distribution": "uniform",
        "time_windows": [(180, 420)],
        "service_time": 5,
        "pickup_ratio": 0.3,
        "deadline_opts": [540]
    },

    # 6. Khó tính 2: 10%, 480-660 (15h-18h)
    "STRICT_AFTERNOON": {
        "ratio": 0.10,
        "demand_range": (5, 12),
        "distribution": "uniform",
        "time_windows": [(480, 660)],
        "service_time": 5,
        "pickup_ratio": 0.3,
        "deadline_opts": [780]
    },

    # 7. Khó tính 3: 10%, 0-120 (7h-9h) - Rất gấp sáng sớm
    "STRICT_EARLY": {
        "ratio": 0.10,
        "demand_range": (5, 10),
        "distribution": "uniform",
        "time_windows": [(0, 120)],
        "service_time": 5,
        "pickup_ratio": 0.3,
        "deadline_opts": [240, 420] # Phải về Hub rất sớm
    },

    # 8. Khó tính 4: 10%, 300-540 (12h-16h)
    "STRICT_NOON": {
        "ratio": 0.10,
        "demand_range": (5, 12),
        "distribution": "uniform",
        "time_windows": [(300, 540)],
        "service_time": 5,
        "pickup_ratio": 0.3,
        "deadline_opts": [600]
    }
}

# ==============================================================================
# BƯỚC 3: MODULE CHUYỂN ĐỔI TỌA ĐỘ (UTM CONVERSION MODULE)
# ==============================================================================

try:
    # <<< THAY ĐỔI QUAN TRỌNG: Sử dụng lớp CRS >>>
    # Tạo đối tượng Hệ quy chiếu (CRS) cho WGS84 từ mã EPSG
    WGS84_CRS = CRS("EPSG:4326")
    
    # Tạo đối tượng CRS cho UTM từ mã EPSG đã cấu hình
    UTM_CRS = CRS(f"EPSG:{GLOBAL_PARAMS['utm_epsg_code']}")
    
    # <<< THAY ĐỔI QUAN TRỌNG: Tạo một đối tượng Transformer >>>
    # Transformer được tối ưu hóa cho việc chuyển đổi lặp đi lặp lại giữa hai hệ quy chiếu
    TRANSFORMER = pyproj.Transformer.from_crs(WGS84_CRS, UTM_CRS, always_xy=True)
    
    PROJ_INITIALIZED = True
    print(f"Initialized CRS Transformer: WGS84 (EPSG:4326) -> UTM (EPSG:{GLOBAL_PARAMS['utm_epsg_code']}).")

except Exception as e:
    PROJ_INITIALIZED = False
    print(f"FATAL ERROR: Could not initialize CRS Transformer. Please check 'utm_epsg_code' in config. Error: {e}")


def convert_wgs84_to_utm(lon, lat):
    """Chuyển đổi một cặp tọa độ WGS84 (kinh độ, vĩ độ) sang UTM (đơn vị mét)."""
    if not PROJ_INITIALIZED:
        return None, None
    try:
        # <<< THAY ĐỔI QUAN TRỌNG: Sử dụng phương thức transform của Transformer >>>
        utm_x, utm_y = TRANSFORMER.transform(lon, lat)
        return utm_x, utm_y
    except Exception as e:
        # Ghi lại cảnh báo nếu một cặp tọa độ cụ thể bị lỗi
        print(f"Warning: Could not transform coordinates ({lon}, {lat}). Error: {e}")
        return None, None
# ==============================================================================
# BƯỚC 4: CORE LOGIC (Sinh dữ liệu khách hàng)
# ==============================================================================

def get_coordinates_around_satellite(satellite, radius_km):
    """
    Sinh ngẫu nhiên một tọa độ WGS84 trong một bán kính (km) quanh một vệ tinh.
    Phân phối theo distribition Normal (Gaussian).
    """
    # 1 độ vĩ tuyến xấp xỉ 111km
    std_dev_in_degrees = radius_km / 111.0
    lat = np.random.normal(satellite['Y'], std_dev_in_degrees)
    lon = np.random.normal(satellite['X'], std_dev_in_degrees)
    return lon, lat

def generate_smart_demand_list(target_total, min_d, max_d, dist_type='uniform'):
    """
    Sinh một danh sách các demand sao cho tổng của chúng gần bằng target_total.
    """
    # ... (Hàm này giữ nguyên, không thay đổi) ...
    if target_total <= 0: return []
    avg_d = (min_d + max_d) / 2
    estimated_count = int(round(target_total / avg_d))
    if estimated_count < 1: estimated_count = 1
    demands = []
    
    for _ in range(estimated_count):
        if dist_type == 'normal':
            sigma = (max_d - min_d) / 6 
            val = np.random.normal(avg_d, sigma)
        else:
            val = random.uniform(min_d, max_d)
        val = int(round(max(min_d, min(val, max_d))))
        demands.append(val)
    
    current_sum = sum(demands)
    diff = target_total - current_sum
    max_iter = abs(diff) * 10
    iter_count = 0
    while diff != 0 and iter_count < max_iter:
        idx = random.randint(0, len(demands) - 1)
        if diff > 0:
            demands[idx] += 1
            diff -= 1
        elif diff < 0:
            if demands[idx] > min_d:
                demands[idx] -= 1
                diff += 1
        iter_count += 1
    if diff != 0 and demands: demands[-1] += diff
    return [d for d in demands if d > 0]

def generate_customers_by_profiles(satellites, total_demand, profiles, radius):
    """
    Hàm chính để sinh dữ liệu khách hàng dựa trên các profiles đã định nghĩa.
    """
    # ... (Hàm này giữ nguyên, không thay đổi) ...
    print(f"--- Bắt đầu sinh dữ liệu. Tổng Demand mục tiêu: {total_demand} ---")
    customers = []
    customer_counter = 1
    generated_demand_sum = 0
    
    for name, config in profiles.items():
        group_target = int(round(total_demand * config['ratio']))
        if group_target <= 0: continue
        
        demand_list = generate_smart_demand_list(group_target, config['demand_range'][0], config['demand_range'][1], config.get('distribution', 'uniform'))
        
        for d in demand_list:
            parent_sat = random.choice(satellites)
            lon, lat = get_coordinates_around_satellite(parent_sat, radius)
            
            is_pickup = random.random() < config['pickup_ratio']
            c_type = 3 if is_pickup else 2
            deadline = float(random.choice(config['deadline_opts'])) if c_type == 3 else 9999.0
            
            chosen_tw = random.choice(config['time_windows'])
            early, latest = float(chosen_tw[0]), float(chosen_tw[1])
            
            cust = {
                'id': f'C{customer_counter}',
                'Type': c_type, 'X': lon, 'Y': lat,
                'Service Time': config['service_time'], 'Early': early, 'Latest': latest,
                'Demand': d, 'Origin/Dest': 1.0, 'Deadline': deadline, 'Profile': name
            }
            customers.append(cust)
            customer_counter += 1
        generated_demand_sum += sum(demand_list)
    print(f"-> HOÀN TẤT. Số khách hàng đã sinh: {len(customers)}. Tổng Demand đã sinh: {generated_demand_sum}/{total_demand}")
    return customers

# ==============================================================================
# BƯỚC 5: MODULE VẼ BIỂU ĐỒ (VISUALIZATION)
# ==============================================================================

# Hàm vẽ biểu đồ WGS84 (tọa độ gốc)
def visualize_instance_wgs84(df, output_path, radius_km):
    """Vẽ bản đồ trực quan hóa vị trí các điểm trên tọa độ WGS84."""
    print("Đang vẽ biểu đồ WGS84 (kinh độ/vĩ độ)...")
    
    depot = df[df['Type'] == 0]
    satellites = df[df['Type'] == 1]
    delivery_cust = df[df['Type'] == 2]
    pickup_cust = df[df['Type'] == 3]

    fig, ax = plt.subplots(figsize=(12, 10))

    # Vẽ vòng tròn bán kính (tính theo độ)
    radius_deg = radius_km / 111.0
    for _, sat in satellites.iterrows():
        circle = patches.Circle((sat['X'], sat['Y']), radius_deg, 
                                linewidth=1, edgecolor='blue', facecolor='blue', alpha=0.05)
        ax.add_patch(circle)
    
    # Vẽ các điểm
    ax.scatter(delivery_cust['X'], delivery_cust['Y'], c='green', s=15, alpha=0.6, label='Delivery')
    ax.scatter(pickup_cust['X'], pickup_cust['Y'], c='orange', s=25, alpha=0.8, label='Pickup', marker='P')
    ax.scatter(satellites['X'], satellites['Y'], c='blue', s=150, marker='^', edgecolors='black', label='Satellite', zorder=5)
    ax.scatter(depot['X'], depot['Y'], c='red', s=200, marker='s', edgecolors='black', label='Depot', zorder=10)
    
    ax.set_title(f'WGS84 Coordinate Visualization (Lat/Lon)\nTotal Customers: {len(df) - len(depot) - len(satellites)}', fontsize=14)
    ax.set_xlabel('Longitude (X)')
    ax.set_ylabel('Latitude (Y)')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_aspect('equal', adjustable='datalim')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"-> Biểu đồ WGS84 đã được lưu tại: {output_path}")

# <<< THÊM MỚI: Hàm vẽ biểu đồ UTM (tọa độ mét) >>>
def visualize_instance_utm(df, output_path, radius_km):
    """Vẽ bản đồ trực quan hóa vị trí các điểm trên tọa độ UTM."""
    print("Đang vẽ biểu đồ UTM (mét)...")
    
    depot = df[df['Type'] == 0]
    satellites = df[df['Type'] == 1]
    delivery_cust = df[df['Type'] == 2]
    pickup_cust = df[df['Type'] == 3]

    fig, ax = plt.subplots(figsize=(12, 12)) # Thường làm hình vuông sẽ đẹp hơn

    # Vẽ vòng tròn bán kính (tính bằng mét)
    radius_m = radius_km * 1000
    for _, sat in satellites.iterrows():
        circle = patches.Circle((sat['X'], sat['Y']), radius_m, 
                                linewidth=1, edgecolor='blue', facecolor='blue', alpha=0.05)
        ax.add_patch(circle)
    
    # Vẽ các điểm
    ax.scatter(delivery_cust['X'], delivery_cust['Y'], c='green', s=15, alpha=0.6, label='Delivery')
    ax.scatter(pickup_cust['X'], pickup_cust['Y'], c='orange', s=25, alpha=0.8, label='Pickup', marker='P')
    ax.scatter(satellites['X'], satellites['Y'], c='blue', s=150, marker='^', edgecolors='black', label='Satellite', zorder=5)
    ax.scatter(depot['X'], depot['Y'], c='red', s=200, marker='s', edgecolors='black', label='Depot', zorder=10)
    
    ax.set_title(f'UTM Coordinate Visualization (meters)\nTotal Customers: {len(df) - len(depot) - len(satellites)}', fontsize=14)
    ax.set_xlabel('UTM Easting (X meters)')
    ax.set_ylabel('UTM Northing (Y meters)')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)
    # Rất quan trọng: Giữ tỉ lệ 1:1 cho tọa độ mét
    ax.set_aspect('equal', adjustable='box') 

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"-> Biểu đồ UTM đã được lưu tại: {output_path}")

# ==============================================================================
# BƯỚC 6: HÀM MAIN - ĐIỀU PHỐI TOÀN BỘ QUY TRÌNH
# ==============================================================================
def process_and_save_dataframe(df, output_dir, filename):
    """
    Hàm tiện ích để chuẩn hóa cột, điền giá trị trống và lưu DataFrame ra file CSV.
    """
    column_order = ['Type', 'X', 'Y', 'Service Time', 'Early', 'Latest', 'Demand', 'Origin/Dest', 'Deadline', 'FE Cap', 'SE Cap']
    for col in column_order:
        if col not in df.columns:
            df[col] = np.nan
            
    df = df[column_order]
    df.loc[df['Type'] == 1, 'Service Time'] = GLOBAL_PARAMS["satellite_service_time"]
    df = df.fillna('')
    
    int_cols = ['Type', 'Service Time', 'Early', 'Latest', 'Demand', 'Deadline']
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, filename)
    df.to_csv(csv_path, index=False)
    print(f"-> File CSV đã được lưu tại: {csv_path}")
    return df
def main(args):
    """Hàm chính điều phối các bước: Đọc -> Sinh -> Chuyển đổi -> Lưu -> Vẽ."""
    
    # ... (Phần 1 và 2: Đọc và Sinh dữ liệu giữ nguyên) ...
    try:
        base_df = pd.read_csv(args.input_file)
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file đầu vào '{args.input_file}'")
        return

    depot_df = base_df[base_df['Type'] == 0].copy()
    satellites_df = base_df[base_df['Type'] == 1].copy()
    satellites_list = satellites_df[['X', 'Y']].to_dict('records')

    # 2. Sinh dữ liệu khách hàng với tọa độ WGS84
    customers_data = generate_customers_by_profiles(
        satellites_list, 
        args.total_demand, 
        CUSTOMER_PROFILES, 
        GLOBAL_PARAMS["distribution_radius_km"]
    )
    customers_df = pd.DataFrame(customers_data)

    # 3. Xử lý và lưu DataFrame WGS84
    print("\n--- Xử lý file WGS84 (tọa độ gốc) ---")
    df_wgs84 = pd.concat([depot_df, satellites_df, customers_df], ignore_index=True)
    processed_df_wgs84 = process_and_save_dataframe(df_wgs84, args.output_dir, GLOBAL_PARAMS["default_output_filename_wgs84"])

    # 4. Xử lý và lưu DataFrame UTM
    print("\n--- Xử lý file UTM (tọa độ mét) ---")
    if not PROJ_INITIALIZED:
        print("Bỏ qua việc tạo file UTM do lỗi khởi tạo projection.")
    else:
        df_utm = df_wgs84.copy()
        utm_coords = df_utm.apply(lambda row: convert_wgs84_to_utm(row['X'], row['Y']), axis=1)
        df_utm[['X', 'Y']] = pd.DataFrame(utm_coords.tolist(), index=df_utm.index)
        processed_df_utm = process_and_save_dataframe(df_utm, args.output_dir, GLOBAL_PARAMS["default_output_filename_utm"])
    
    # 5. Vẽ các biểu đồ
    # 5.1 Vẽ biểu đồ WGS84
    plot_path_wgs84 = os.path.join(args.output_dir, GLOBAL_PARAMS["plot_filename_wgs84"])
    plot_df_wgs84 = processed_df_wgs84.copy()
    for col in ['Type', 'X', 'Y']:
        plot_df_wgs84[col] = pd.to_numeric(plot_df_wgs84[col])
    visualize_instance_wgs84(plot_df_wgs84, plot_path_wgs84, GLOBAL_PARAMS["distribution_radius_km"])

    # 5.2 <<< THÊM MỚI: Vẽ biểu đồ UTM >>>
    if PROJ_INITIALIZED:
        plot_path_utm = os.path.join(args.output_dir, GLOBAL_PARAMS["plot_filename_utm"])
        plot_df_utm = processed_df_utm.copy()
        for col in ['Type', 'X', 'Y']:
            plot_df_utm[col] = pd.to_numeric(plot_df_utm[col])
        visualize_instance_utm(plot_df_utm, plot_path_utm, GLOBAL_PARAMS["distribution_radius_km"])
    
    # Đóng tất cả cửa sổ plot để chương trình kết thúc
    plt.close('all')

if __name__ == "__main__":
    # Thiết lập trình phân tích cú pháp dòng lệnh để dễ dàng thay đổi tham số
    parser = argparse.ArgumentParser(description="Generate 2E-VRP-PDD instances with WGS84 and UTM coordinates.")
    parser.add_argument('-i', '--input-file', type=str, default=GLOBAL_PARAMS["default_input_file"],
                        help="Path to the base CSV file containing Depot and Satellites.")
    parser.add_argument('-o', '--output-dir', type=str, default='output_instance',
                        help="Directory to save the generated files.")
    parser.add_argument('-d', '--total-demand', type=int, default=2830,
                        help="Target total demand for all generated customers.")
    args = parser.parse_args()
    main(args)