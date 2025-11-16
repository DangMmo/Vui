# --- START OF FILE visualizer.py ---

import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
from data_structures import Solution, SERoute
import os # <<< IMPORT MỚI >>>

def _get_unique_nodes_from_fe_schedule(schedule: List[Dict]) -> List[int]:
    if not schedule: return []
    path_nodes = [schedule[0]['node_id']]
    for event in schedule[1:]:
        if event['node_id'] != path_nodes[-1]: path_nodes.append(event['node_id'])
    return path_nodes

# <<< THÊM THAM SỐ save_dir ĐỂ LƯU FILE >>>
def visualize_solution(solution: Solution, save_dir: str = None):
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
    
    ax.set_title(f"2E-VRP Solution Visualization (Total Cost: {solution.get_objective_cost():.2f})", fontsize=18)
    ax.set_xlabel("X Coordinate", fontsize=12)
    ax.set_ylabel("Y Coordinate", fontsize=12)
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_aspect('equal', adjustable='box')
    
    plt.tight_layout()

    # <<< LOGIC MỚI: LƯU BIỂU ĐỒ NẾU CÓ ĐƯỜNG DẪN >>>
    if save_dir:
        file_path = os.path.join(save_dir, "solution_visualization.png")
        plt.savefig(file_path, dpi=300)
        print(f"Solution visualization saved to {file_path}")

    # plt.show() # Tạm thời không show ở đây, để hàm main quản lý
# --- END OF FILE visualizer.py ---