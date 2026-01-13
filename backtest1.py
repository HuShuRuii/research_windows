import pandas as pd
import numpy as np
import statsmodels.api as sm
from enum import Enum
import time
import re
import os
import sys
import draw
import backtest
from datetime import datetime, timedelta
import read_xtdata

__all__ = [

]
class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

class OrderStatus(Enum):
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class Period (Enum):
    DAY = '1d'
    WEEK = '1w'
    # MONTH = '1month'
    YEAR = '1y'
    MINUTE="1m"
    TICK="tick"
    
    def __str__(self):
        return self.name.lower()

    
class OrderFilled: 
    def __init__(self,symbol:str,quantity:int,price:float,time:str):
        self.symbol=symbol
        self.quantity=quantity
        self.price=price
        # buy or sell positive sell negative quantity
        self.time=time

class OrderRequest:
    def __init__(self,symbol:str,quantity:int,type:OrderType,action:OrderSide,time:pd.datetime,price:float=None):
        self.symbol=symbol
        self.quantity=quantity
        self.price=price
        self.action=action  # buy or sell
        self.type=type
        # market or limit
        # if is the market order, price is None
        self.time =time

def min_reachable_value(series:pd.Series,threshold:float)->float:
    sorted_series=series.sort_values()
    for value in sorted_series:
        if abs(value)<=threshold:
            return value
    return sorted_series.iloc[-1]

# ChildProcessError signal(data:pd.DataFrame,threshold:float=2.0)->pd.Series:
#     signals = pd.Series(0, index=data.index)
#     signals[data['zscore'] > threshold] = threshold  # 多头信号
#     signals[data['zscore'] < -threshold] = - threshold  # 空头信号
#     return signals

class DataHandler:
    def __init__(self):
        pass
    
    def get_data(self,symbols:list[str],start:str,end:str,period:Period=Period.MINUTE)->pd.DataFrame:
        xtdata.download_history_data2(symbols,str(period),start_time=start,end_time=end)
        for symbol in symbols:
            xtdata.subscribe_quote(symbol, period=str(period), start_time=start, end_time=end, callback=None)
        data=xtdata.get_market_data_ex([],symbols,period=str(period),start_time=start,end_time=end)
        time.sleep(1)
        for symbol in symbols:
            data[symbol]["time"]=pd.todatetime(data[symbol]["time"],unit='ms')
        return data

class Strategy:
    def __init__(self,name:str,window:int=20):
        self.name=name
        self.window=window
        
    def generate_signals(self,data:pd.DataFrame)->pd.Series:
        raise NotImplementedError("Should implement generate_signals()!")

class OrderGenerator:
    def __init__(self,threshold:float=1.2):
        self.threshold=threshold
    
    def generate_order(self,signal:float,symbols:list[str],time:pd.datetime,price:dict)->list[OrderRequest]|None:
        request:list[OrderRequest]=[]
        if signal > self.threshold:
            for symbol in symbols:
                request.append(OrderRequest(
                    symbol=symbol,quantity=1,type=OrderType.MARKET,order_action=OrderSide.BUY,price=price,time=time))
        elif signal < -self.threshold:
            for symbol in symbols:
                request.append(OrderRequest(
                    symbol=symbol,quantity=1,type=OrderType.MARKET,order_action=OrderSide.SELL,price=price,time=time))
        return request 

class Portfolio:
    def __init__(self,fee_rate:float=0.0003,
                 initial_capital:float=100000.0,
                 margin_requirement:float=0.2,
                 interest_rate:float=0.00):
        self.fee_rate=fee_rate
        self.holdings={}
        self.cash=initial_capital
        self.total_value=0.0
        self.holding_cost={} 
        self.margin_requirement=margin_requirement
        self.interest_rate=interest_rate
        self.total_value_history=[]
        self.trading_history:list[OrderFilled]=[]
        
    def update_total_value(self,price_dict:dict)->float:
        total_value=self.cash
        for symbol,quantity in self.holdings.items():
            if symbol in price_dict:
                total_value += quantity * price_dict[symbol]
        self.total_value=total_value
        return total_value
    
    def market_update(self,price_dict:dict)->None:
        self.total_value=self.update_total_value(price_dict)
        self.total_value_history.append(self.total_value)
        
    def order_settlement(self,order:OrderFilled)->None:
        if order.symbol not in self.holdings:
            self.holdings[order.symbol]=0
            self.holding_cost[order.symbol]=0.0
        self.holdings[order.symbol] += order.quantity
        self.cash-= order.quantity * order.price * (1 + self.fee_rate)
        self.trading_history.append(order)
                
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

class OrderExecutor:
    def __init__(self,latency:pd.Timedelta=datetime.timedelta(seconds=0),price_dict:dict={}):
        self.latency=latency
        self.price_dict=price_dict
        
    def simple_execute(self,order:OrderRequest)->OrderFilled:
        time=order.time + self.latency
        return OrderFilled(order.symbol,order.quantity,order.price,time)
    
class PerformanceSummary:
    def __init__(self,history:pd.DataFrame,period:Period):
        self.history=history
        self.performance={}
        self.returns=0.0
        self.drawdowns=0.0
        self.sharpes=0.0
        self.calmar_ratios=0.0
        self.volatilities=0.0
        self.period=period
    
    def as_dict(self):
        return {
            "returns": self.returns,
            "drawdowns": self.drawdowns,
            "sharpes": self.sharpes,
            "calmar_ratios": self.calmar_ratios,
            "volatilities": self.volatilities
        }
    pass

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
    
    def run_backtest(self, symbols: list[str], start: str, end: str,period:Period) -> pd.DataFrame:
    
        data = self.data_handler.get_data(symbols, start, end,period)
        
        signals = self.strategy.generate_signals(data)
   
        for date in data[symbols[0]].index:
            current_prices = {sym: data[sym].loc[date, 'close'] for sym in symbols}
            
            daily_signals = signals.loc[date]
            
            request=self.order_generator.generate_order(daily_signals,symbols,current_prices,date,current_prices)
            if request is not None:
                for order_request in request:
                    if self.risk_manager.check_risk(self.portfolio,order_request):
                        order_filled=self.execution_handler.simple_execute(order_request)
                        self.portfolio.order_settlement(order_filled)

            self.portfolio.market_update(current_prices)
        
        return self.portfolio.total_value_history

def max_drawdown(equity_curve:pd.Series)->float:
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    return max_drawdown

def annualized_return(equity_curve:pd.Series, periods_per_year:int=252)->float:
    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    num_years = len(equity_curve) / periods_per_year
    annualized_return = (1 + total_return) ** (1 / num_years) - 1
    return annualized_return

def return_volatility(equity_curve:pd.Series, periods_per_year:int=252)->float:
    returns = equity_curve.pct_change().dropna()
    annualized_volatility = returns.std() * np.sqrt(periods_per_year)
    return annualized_volatility

def return_simple(equity_curve:pd.Series)->float:
    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    return total_return

def sharpe_ratio(equity_curve:pd.Series, risk_free_rate:float=0.0, periods_per_year:int=252)->float:
    returns = equity_curve.pct_change().dropna()
    excess_returns = returns - (risk_free_rate / periods_per_year)
    annualized_return = excess_returns.mean() * periods_per_year
    annualized_volatility = excess_returns.std() * np.sqrt(periods_per_year)
    if annualized_volatility == 0:
        return np.nan
    sharpe_ratio = annualized_return / annualized_volatility
    return sharpe_ratio

def calmar_ratio(equity_curve:pd.Series, periods_per_year:int=252)->float:
    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    num_years = len(equity_curve) / periods_per_year
    annualized_return = (1 + total_return) ** (1 / num_years) - 1
    max_dd = abs(max_drawdown(equity_curve))
    if max_dd == 0:
        return np.nan
    calmar_ratio = annualized_return / max_dd
    return calmar_ratio

def rolling_residuals(df:pd.DataFrame, col_y:str, col_x:str, K:int=10):
    
    residuals = pd.Series(index=df.index, dtype='float64')
    standardized_residuals = pd.Series(index=df.index, dtype='float64')
    
    # 从第 K 行开始（索引 K-1 是第 K 个数据，但回归需要前 K 行）
    for i in range(K, len(df)):
        y_hist = df[col_y].iloc[i-K:i].values
        x_hist = df[col_x].iloc[i-K:i].values
        
        # 添加常数项（截距）
        x_hist_sm = sm.add_constant(x_hist)
        
        try:
            # OLS 回归.params
            model = sm.OLS(y_hist, x_hist_sm, missing='drop').fit()
            alpha, beta = model.params
            
            # 2. 用当天数据计算残差（注意：用 df.iloc[i]）
            y_today = df[col_y].iloc[i]
            x_today = df[col_x].iloc[i]
            pred_today = alpha + beta * x_today
            residual = y_today - pred_today
            residuals.iloc[i] = residual
            
        except:
            residuals.iloc[i] = np.nan
    
    # 3. 标准化残差（用滚动标准差）
    residual_std = residuals.rolling(window=K, min_periods=1).std()
    standardized_residuals = residuals / residual_std
    
    return standardized_residuals