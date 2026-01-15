from enum import Enum
import pandas as pd
import datetime
class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class Tick:
    def __init__(self,time:pd.Timestamp,symbol:str,bidPrice:list[float],askPrice:list[float],askVol:list[int],bidVol:list[int],lastPrice:float=None):
        self.symbol=symbol
        self.time=time
        self.bidPrice=bidPrice 
        self.askPrice=askPrice
        self.askVol=askVol
        self.bidVol=bidVol
        self.lastPrice=lastPrice

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
    def __init__(self,symbol:str,quantity:int,price:float,time:str,commision:float=0.0):    
        self.symbol=symbol
        self.quantity=quantity
        self.price=price
        self.commision=0.0
        # buy or sell positive sell negative quantity
        self.time=time

class OrderRequest:
    def __init__(self,symbol:str,quantity:int,side:OrderSide,type:OrderType,action:OrderSide,time:datetime.datetime,price:float=None):
        self.symbol=symbol
        self.quantity=quantity
        self.price=price
        self.action=action  # buy or sell
        self.type=type
        self.side=side
        # market or limit
        # if is the market order, price is None
        self.time =time
        
        