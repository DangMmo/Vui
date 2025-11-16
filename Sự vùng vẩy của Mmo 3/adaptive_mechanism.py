# --- START OF FILE adaptive_mechanism.py ---

import random
from typing import List, Dict, Callable

class Operator:
    """
    Một lớp để đóng gói một toán tử, cùng với các thông số học thích ứng của nó.
    """
    def __init__(self, name: str, function: Callable):
        self.name = name
        self.function = function      # Tham chiếu đến hàm toán tử
        self.weight = 1.0             # Trọng số, ban đầu bằng nhau
        self.score = 0.0              # Điểm số trong segment hiện tại
        self.times_used = 0           # Số lần sử dụng trong segment hiện tại

class AdaptiveOperatorSelector:
    """
    Quản lý việc lựa chọn và cập nhật trọng số cho các toán tử destroy và repair.
    """
    def __init__(self, destroy_operators: Dict[str, Callable], repair_operators: Dict[str, Callable], reaction_factor: float = 0.1):
        self.destroy_ops = [Operator(name, func) for name, func in destroy_operators.items()]
        self.repair_ops = [Operator(name, func) for name, func in repair_operators.items()]
        self.reaction_factor = reaction_factor

    def _select_operator(self, operators: List[Operator]) -> Operator:
        """
        Thực hiện Roulette Wheel Selection để chọn một toán tử.
        """
        total_weight = sum(op.weight for op in operators)
        pick = random.uniform(0, total_weight)
        current = 0
        for op in operators:
            current += op.weight
            if current > pick:
                op.times_used += 1
                return op
        # Fallback in case of rounding errors
        return operators[-1]

    def select_destroy_operator(self) -> Operator:
        return self._select_operator(self.destroy_ops)

    def select_repair_operator(self) -> Operator:
        return self._select_operator(self.repair_ops)

    def update_scores(self, destroy_op: Operator, repair_op: Operator, sigma: float):
        """
        Cập nhật điểm cho cặp toán tử đã được sử dụng.
        """
        destroy_op.score += sigma
        repair_op.score += sigma

    def update_weights(self):
        """
        Cập nhật trọng số cho tất cả các toán tử sau khi kết thúc một segment.
        """
        for op_list in [self.destroy_ops, self.repair_ops]:
            for op in op_list:
                if op.times_used > 0:
                    op.weight = (1 - self.reaction_factor) * op.weight + \
                                self.reaction_factor * (op.score / op.times_used)
                # Reset score và times_used cho segment tiếp theo
                op.score = 0
                op.times_used = 0

# --- END OF FILE adaptive_mechanism.py ---

