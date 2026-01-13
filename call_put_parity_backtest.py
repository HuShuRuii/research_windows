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

OPTION_CODE_CALL="IO2512-C-3400.IF"
OPTION_CODE_PUT="IO2512-P-3400.IF"
CONTRACT_CODE="IF2512.IF"
STRIKE_PRICE=3400.0
MARGIN=0.5
class call_put_arbitrage_strategy(backtest.Strategy):
    def __init__(self,name:str,window:int=20,
                 option_code_call:str=OPTION_CODE_CALL,option_code_put:str=OPTION_CODE_PUT,
                 contract_code:str=CONTRACT_CODE,strike_price:float=STRIKE_PRICE):
        super().__init__(name,window)
        self.option_code_call=option_code_call
        self.option_code_put=option_code_put
        self.contract_code=contract_code
        self.strike_price=strike_price
        
    def generate_signals(self,data:pd.DataFrame)->pd.Series:
        signals=pd.DataFrame(index=data[self.contract_code].index)
        signals["residual"]=(data[self.option_code_call]["close"] - data[self.option_code_put]["close"]
                             - data[self.contract_code]["close"] + self.strike_price["close"])
        signals["zscore"]= (signals["residual"] - signals["residual"].rolling(window=self.window).mean()) / signals["residual"].rolling(window=self.window).std()
        return signals["zscore"]
    
    
class call_put_order_generator(backtest.OrderGenerator):
    def __init__(self, threshold: float = 1.2):
        super().__init__(threshold)
    
    def generate_order(self,signal:float,symbols:list[str],time:pd.datetime,price:dict,account:backtest.Account)->list[backtest.OrderRequest]|None:
        request:list[backtest.OrderRequest]=[]
        amount=int(account.cash //(price[CONTRACT_CODE]) * MARGIN)
        if signal > self.threshold:
            if account.holdings[CONTRACT_CODE]<=0:
                amount-=account.holdings[CONTRACT_CODE]
            request.append(backtest.OrderRequest(
                symbol=CONTRACT_CODE,quantity=amount,type=backtest.OrderType.MARKET,
                order_action=backtest.OrderSide.BUY,price=price[CONTRACT_CODE],time=time))
            request.append(backtest.OrderRequest(
                symbol=OPTION_CODE_CALL,quantity=amount,type=backtest.OrderType.MARKET,
                order_action=backtest.OrderSide.SELL,price=price[OPTION_CODE_CALL],time=time))
            request.append(backtest.OrderRequest(
                symbol=OPTION_CODE_PUT,quantity=amount,type=backtest.OrderType.MARKET,
                order_action=backtest.OrderSide.BUY,price=price[OPTION_CODE_PUT],time=time))
        elif signal < -self.threshold:
            if account.holdings[CONTRACT_CODE]>=0:
                amount+=account.holdings[CONTRACT_CODE]
            request.append(backtest.OrderRequest(
                symbol=CONTRACT_CODE,quantity=amount,type=backtest.OrderType.MARKET,
                order_action=backtest.OrderSide.SELL,price=price[CONTRACT_CODE],time=time))
            request.append(backtest.OrderRequest(
                symbol=OPTION_CODE_CALL,quantity=amount,type=backtest.OrderType.MARKET,
                order_action=backtest.OrderSide.BUY,price=price[OPTION_CODE_CALL],time=time))
            request.append(backtest.OrderRequest(
                symbol=OPTION_CODE_PUT,quantity=amount,type=backtest.OrderType.MARKET,
                order_action=backtest.OrderSide.SELL,price=price[OPTION_CODE_PUT],time=time))
        return request 

datahandler=backtest.DataHandlBUY
portfolio=backtest.Portfolio(initial_capital=1000000)
strategy=call_put_arbitrage_strategy(name="call_put_parity_strategy",window=20)
order_generator=call_put_order_generator(threshold=1.2)
execution_handler=backtest.OrderExecutor()
risk_manager=backtest.RiskManager()
backtest_engine=backtest.BacktestEngine(
    data_handler=datahandler,
    strategy=strategy,
    portfolio=portfolio,
    execution_handler=execution_handler,
    risk_manager=risk_manager,
    order_generator=order_generator
)

res=backtest_engine.run_backtest([OPTION_CODE_CALL,OPTION_CODE_PUT,CONTRACT_CODE])