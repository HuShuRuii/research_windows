import pandas as pd
import numpy as np
from .type_declare import OrderFilled

class Account:
    def __init__(self,
                 cash:float=100000.0,
                 holdings:dict={},
                 holding_price:dict={},
                 holding_cost:dict={},
                 total_value:float=0.0):
        self.cash=cash
        self.holdings=holdings
        self.holding_price=holding_price
        self.total_value=total_value
        self.holding_cost=holding_cost
    
    def update_total_value(self)->float:
        total_value=self.cash
        for symbol,quantity in self.holdings.items():
            if symbol in self.price_dict:
                total_value += quantity * self.price_dict[symbol]
        self.total_value=total_value
        return total_value

class Portfolio:
    def __init__(self,
                 fee_rate:float=0.0003,
                 initial_capital:float=100000.0,
                 margin_requirement:float=0.2,
                 interest_rate:float=0.00,
                 borrow_cost:float=0.0):
        self.fee_rate=fee_rate
        self.account=Account(
            cash=initial_capital,
            holdings={},
            holding_price={},
            holding_cost={},
            total_value=initial_capital
        )
        # do we have to pay the short interest rate?
        self.margin_requirement=margin_requirement
        self.interest_rate=interest_rate
        self.borrow_cost=borrow_cost
        self.total_value_history=[]
        self.trading_history:list[OrderFilled]=[]
        
    def get_account_snapshot(self)->Account:
        return self.account
    
    def market_update(self,price_dict:dict)->None:
        for symbol in self.account.holdings.keys():
                if symbol in price_dict:
                    self.account.holding_price[symbol]= price_dict[symbol]
                else:
                    raise ValueError(f"Price for symbol {symbol} not found in price_dict")
        if self.borrow_cost>0.0:
            # calculate the borrow cost for short positions
            for symbol,quantity in self.account.holdings.items():
                if quantity<0:
                    self.account.cash -= abs(quantity) * self.account.holding_price[symbol] * self.borrow_cost
        self.total_value=self.account.update_total_value()
        
        # self.total_value_history.append(self.total_value)
        
    def order_settlement(self,order:OrderFilled)->None:
        if order.symbol not in self.holdings:
            self.holdings[order.symbol]=0
            self.holding_cost[order.symbol]=0.0
        self.holdings[order.symbol] += order.quantity
        self.holding_cost[order.symbol] += ((order.quantity * order.price+ self.account.holding_cost[order.symbol] *self.account.holdings[order.symbol])/
            (self.account.holdings[order.symbol]+ order.quantity))
        self.cash-= order.quantity * order.price + order.commision
        self.trading_history.append(order)
        
    def add_to_history(self)->None:
        self.total_value_history.append(self.account.total_value)
               