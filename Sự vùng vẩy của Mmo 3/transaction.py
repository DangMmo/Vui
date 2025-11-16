# --- START OF FILE transaction.py ---

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Union

if TYPE_CHECKING:
    from data_structures import SERoute, FERoute, Solution

class RouteMemento:
    """
    Lưu trữ trạng thái có thể khôi phục của một đối tượng Route (cả SE và FE).
    """
    def __init__(self, route: Union["SERoute", "FERoute"]):
        # Kiểm tra xem có phải là SERoute không bằng cách tìm thuộc tính 'nodes_id'
        if hasattr(route, 'nodes_id'):
            self.nodes_id = route.nodes_id.copy()
            self.total_dist = route.total_dist
            self.total_travel_time = route.total_travel_time # <<< DÒNG MỚI >>>
            self.total_load_pickup = route.total_load_pickup
            self.total_load_delivery = route.total_load_delivery
            self.service_start_times = route.service_start_times.copy()
            self.waiting_times = route.waiting_times.copy()
            self.forward_time_slacks = route.forward_time_slacks.copy()
            self.serving_fe_routes = route.serving_fe_routes.copy()
        # Kiểm tra xem có phải là FERoute không bằng cách tìm thuộc tính 'schedule'
        elif hasattr(route, 'schedule'):
            self.serviced_se_routes = route.serviced_se_routes.copy()
            self.schedule = route.schedule.copy()
            self.total_dist = route.total_dist
            self.total_time = route.total_time # Đây là duration, giữ nguyên tên
            self.total_travel_time = route.total_travel_time # <<< DÒNG MỚI >>>
            self.route_deadline = route.route_deadline
        else:
            raise TypeError(f"Unsupported route type for Memento: {type(route)}")


class ChangeContext:
    """
    Quản lý một "giao dịch" các thay đổi trên một đối tượng Solution.
    Cho phép thực hiện rollback nếu nước đi bị từ chối.
    """
    def __init__(self, solution: "Solution"):
        self.solution = solution
        self.affected_routes_mementos: Dict[Union["SERoute", "FERoute"], RouteMemento] = {}
        self.newly_created_routes: List[Union["SERoute", "FERoute"]] = []
        self.removed_routes: List[Union["SERoute", "FERoute"]] = []

    def backup_route(self, route: Union["SERoute", "FERoute"]):
        """Sao lưu trạng thái của một route TRƯỚC KHI nó bị thay đổi."""
        if route not in self.affected_routes_mementos:
            self.affected_routes_mementos[route] = route.backup()

    def track_new_route(self, route: Union["SERoute", "FERoute"]):
        """Theo dõi một route mới được tạo ra trong giao dịch này."""
        self.newly_created_routes.append(route)

    def track_removed_route(self, route: Union["SERoute", "FERoute"]):
        """Theo dõi một route đã bị xóa trong giao dịch này."""
        self.removed_routes.append(route)

    def rollback(self):
        """Hoàn tác tất cả các thay đổi đã được theo dõi trong context này."""
        from data_structures import SERoute, FERoute
        
        for route in self.removed_routes:
            if isinstance(route, SERoute):
                if route not in self.solution.se_routes: self.solution.se_routes.append(route)
            elif isinstance(route, FERoute):
                if route not in self.solution.fe_routes: self.solution.fe_routes.append(route)

        for route in self.newly_created_routes:
            if isinstance(route, SERoute):
                if route in self.solution.se_routes: self.solution.se_routes.remove(route)
            elif isinstance(route, FERoute):
                if route in self.solution.fe_routes: self.solution.fe_routes.remove(route)

        for route, memento in self.affected_routes_mementos.items():
            route.restore(memento)
        
        self.solution.update_customer_map()
# --- END OF FILE transaction.py ---