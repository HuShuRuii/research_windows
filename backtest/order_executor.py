import pandas as pd
import numpy as np
from datetime import datetime,timedelta
from .type_declare import OrderRequest, OrderFilled, OrderType, OrderSide,Tick

class OrderExecutor:
    def __init__(self,commision_rate:float=0,latency:pd.Timedelta=timedelta(seconds=0),price_dict:dict={}):
        self.latency=latency
        self.price_dict=price_dict
        self.commision_rate=commision_rate # percentage commission rate
        
    def simple_execute(self,order:OrderRequest)->OrderFilled:
        time=order.time + self.latency
        q=order.quantity if order.action==OrderSide.BUY else -order.quantity
        return OrderFilled(order.symbol,q,order.price,time)
    
    def execute_with_tick(self,order:OrderRequest,current_time:datetime,tick:Tick)->OrderFilled|None:
        total:float=0
        settled_quan:int=0
        if order.side==OrderSide.BUY:
            price=tick.askPrice
            volume=tick.askVol
        else:
            price=tick.bidPrice
            volume=tick.bidVol
        for i in range(len(price)):
            trade_volume=min(quantity,volume[i])
            if order.price is not None:
                if (type==OrderSide.BUY and price[i]>order.price) or (type==OrderSide.SELL and price[i]<order.price):
                    break
            total+=trade_volume*price[i]
            quantity-=trade_volume
            settled_quan+=trade_volume
        if settled_quan==0:
            return None
        commision=self.commision_rate*total
        return OrderFilled(order.symbol,settled_quan if order.side==OrderSide.BUY else -settled_quan,
                           total/settled_quan,current_time,commision)
    
    def min_reachable_value(series:pd.Series,threshold:float)->float:
        sorted_series=series.sort_values()
        for value in sorted_series:
            if abs(value)<=threshold:
                return value
        return sorted_series.iloc[-1]
