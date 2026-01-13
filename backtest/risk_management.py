from .portfolio import Portfolio
from .type_declare import OrderRequest
class RiskManager:
    def __init__(self,max_drawdown:float=0.2,max_position_size:float=0.1,fee:float=0.0003):
        self.max_drawdown=max_drawdown
        self.max_position_size=max_position_size
        self.fee=fee
        
    def check_risk(self,portfolio:Portfolio,proposed_order:OrderRequest)->bool:
        # Check position size
        proposed_value=(1+self.fee)*proposed_order.quantity * proposed_order.price
        if abs(proposed_value) > self.max_position_size * portfolio.total_value:
            return False
        # # Check drawdown (simplified example)
        # if len(portfolio.total_value_history)>0:
        #     peak_value=max(portfolio.total_value_history)
        #     projected_value=portfolio.total_value + proposed_value
        #     drawdown=(peak_value - projected_value) / peak_value
        #     if drawdown > self.max_drawdown:
        #         return False
        return True