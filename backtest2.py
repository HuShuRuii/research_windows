import pandas as pd
import numpy as np
import datetime
import statsmodels.api as sm
from enum import Enum

def backtest_pair(history:pd.DataFrame, entry_threshold:float=1.2, exit_threshold:float=-1.2, initial_capital:float=100000.0,fee:float=0.0003,useage:float=0.8,col_x:str="close_A",col_y:str="close_B",K:int=10)->pd.DataFrame:
    # used for pair trading backtest
    capital = initial_capital
    position_x=position_y =0  # 持仓数量
    entry_price_x=entry_price_y =0  # 进场价格
    equity_curve = []  # 资金曲线记录
    history=history.copy()
    history["cor_residual"]=rolling_residuals(history,col_x,col_y,K=K)
    for index, row in history.iterrows():
        price_x = row[col_x] 
        price_y = row[col_y]
        score_value = row['cor_residual']
        # 进场条件
        if position_x != 0 and score_value < exit_threshold:
            capital += position_x * (price_x - entry_price_x)+ position_y * (price_y - entry_price_y)
            position_x = 0
            position_y = 0  
            
        amount_y= useage * capital / price_y
        amount_x= useage * capital / price_x
        if position_x == 0 :
            if score_value > entry_threshold:
            # short y, long x
                position_x = amount_x * useage
                entry_price_x = price_x
                position_y = -amount_y *useage
                entry_price_y = price_y
                capital -= fee * (abs(position_x)*price_x + abs(position_y)*price_y)
            
            elif score_value < -entry_threshold:
            # long y, short x
                position_x = -amount_x * useage
                entry_price_x = price_x
                position_y = amount_y * useage
                entry_price_y = price_y
                capital -= fee * (abs(position_x)*price_x + abs(position_y)*price_y)

        # 记录资金曲线
        equity_curve.append(capital + position_x * (price_x - entry_price_x)+position_y * (price_y - entry_price_y)  
                            if position_x != 0 else capital)

    history['equity_curve'] = equity_curve
    return history

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

def zscore(series: pd.Series,adjust_option: bool=False,halffile:int=10) -> pd.Series:
    ewma_std = series.ewm(halflife=halffile, adjust=adjust_option).std()
    ewma_mean= series.ewm(halflife=halffile, adjust=adjust_option).mean()
    # 可选：将前30日EWMA波动率替换为滚动标准差
    res=(series - ewma_mean)/ ewma_std
    return res

def backtest_cp_parity(history:pd.DataFrame,threshold:float=1.2,  initial_capital:float=100000.0,fee:float=0.0003,useage:float=0.8,K:int=10)->pd.DataFrame:
    # used for pair trading backtest
    list[list[float]] = []
    capital = initial_capital
    position_c=position_p=position_contract =0  # 持仓数量
    entry_price_x=entry_price_y =entry_price_contract=0  # 进场价格
    equity_curve = []  # 资金曲线记录
    history=history.copy()
    for row in history.iterrows():
        score=row["residual_z"]
        price_c= row["close_c"]
        price_p= row["close_p"]
        price_contract=row["close"]
        # 进场条件
        # useage should be approximately 10 since the margin is 8%
        if score<-threshold :
            if position_contract>=0:
                capital += position_c * (price_c - entry_price_x)+ position_p * (price_p - entry_price_y)+ position_contract * (price_contract - entry_price_contract)
                position_c=position_p=position_contract=0
                position_contract= -useage * capital / price_contract
                position_c= position_contract
                position_p= -position_contract
                entry_price_x=price_c
                entry_price_y=price_p
                entry_price_contract=price_contract
                capital -= fee * (abs(position_c)*price_c + abs(position_p)*price_p + abs(position_contract)*price_contract)
            
        elif score>threshold:
            if position_contract<=0:
                capital += position_c * (price_c - entry_price_x)+ position_p * (price_p - entry_price_y)+ position_contract * (price_contract - entry_price_contract)
                position_c=position_p=position_contract=0
                position_contract= useage * capital / price_contract
                position_c= position_contract
                position_p= -position_contract
                entry_price_x=price_c
                entry_price_y=price_p
                entry_price_contract=price_contract
                capital -= fee * (abs(position_c)*price_c + abs(position_p)*price_p + abs(position_contract)*price_contract)
        
        # 记录资金曲线
        equity_curve.append(capital + position_c * (price_c - entry_price_x)+position_p * (price_p - entry_price_y)+ position_contract * (price_contract - entry_price_contract)
                            if position_c != 0 else capital)

    history['equity_curve'] = equity_curve
    return history
