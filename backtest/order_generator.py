import pandas as pd
import numpy as np
from .type_declare import OrderRequest, OrderType, OrderSide
import datetime
from .portfolio import Account
class OrderGenerator:
    def __init__(self,threshold:float=1.2):
        self.threshold=threshold
    
    def generate_order(self,signal:float,symbols:list[str],time:datetime.datetime,price:dict,account:Account)->list[OrderRequest]|None:
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