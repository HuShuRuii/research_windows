from .strategy import Strategy
from .data_handler import DataHandler
from .portfolio import Portfolio
from .order_executor import OrderExecutor
from .risk_management import RiskManager
from .order_generator import OrderGenerator
import pandas as pd
from .performance import PerformanceSummary
from .type_declare import Period

class BacktestEngine:
    def __init__(self, 
                 data_handler: DataHandler,
                 strategy: Strategy,
                 portfolio: Portfolio,
                 execution_handler: OrderExecutor,
                 risk_manager: RiskManager,
                 order_generator:OrderGenerator):
        self.data_handler = data_handler
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution_handler = execution_handler
        self.risk_manager = risk_manager
        self.results = None
        self.order_generator=order_generator
    
    def run_backtest(self, symbols: list[str], start: str="",end: str="",
                     period:Period=Period.MINUTE) -> pd.DataFrame:
    
        data = self.data_handler.get_data(symbols, start, end,period)
        
        signals = self.strategy.generate_signals(data)
   
        for date in data[symbols[0]].index:
            current_prices = {sym: data[sym].loc[date, 'close'] for sym in symbols}
            
            daily_signals = signals.loc[date]
            
            request=self.order_generator.generate_order(daily_signals,symbols,current_prices,date,current_prices,self.portfolio.get_account_snapshot())
            
            if request is not None:
                for order_request in request:
                    if self.risk_manager.check_risk(self.portfolio,order_request):
                        order_filled=self.execution_handler.simple_execute(order_request)
                        self.portfolio.order_settlement(order_filled)
            
            self.portfolio.market_update(current_prices)
            self.portfolio.add_to_history()
            
        
        return PerformanceSummary(pd.Series(self.portfolio.total_value_history))
