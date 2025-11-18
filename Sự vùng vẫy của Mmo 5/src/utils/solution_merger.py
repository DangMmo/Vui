# Đã được tạo ở Giai đoạn 1, giờ kiểm tra lại cho chắc chắn.
# Nội dung file này không thay đổi so với kế hoạch ban đầu.
from __future__ import annotations
from typing import TYPE_CHECKING, List
from ..core.data_structures import Solution 

if TYPE_CHECKING:
    from ..core.problem_parser import ProblemInstance

def merge_solutions(sub_solutions: List[Solution], original_problem: "ProblemInstance") -> Solution:
    """
    Hợp nhất một danh sách các lời giải con thành một lời giải tổng thể.
    """
    merged_solution = Solution(original_problem)
    
    for sub_sol in sub_solutions:
        merged_solution.fe_routes.extend(sub_sol.fe_routes)
        merged_solution.se_routes.extend(sub_sol.se_routes)
        merged_solution.unserved_customers.extend(sub_sol.unserved_customers)
        
    merged_solution.update_customer_map()
    
    print(f"\n--- Merged {len(sub_solutions)} sub-solutions into one final solution ---")
    return merged_solution