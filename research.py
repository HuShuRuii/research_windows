import pandas as pd
import numpy as np
from xtquant import xtdata
def exceedance_correlation(A:pd.DataFrame,B:pd.DataFrame,threshold:float=1.5,t:str="time"):
    A=A.copy()
    B=B.copy()
    if threshold>0:
        A_exceed=A[A["z_return"]>threshold]
        B_exceed=B[B["z_return"]>threshold]
    else:
        A_exceed=A[A["z_return"]<threshold]
        B_exceed=B[B["z_return"]<threshold]
    merged=pd.merge(A_exceed[[t,"z_return"]],B_exceed[[t,"z_return"]],on=t,suffixes=("_A","_B"))
    if merged.shape[0]==0:
        return np.nan
    merged["z_return_A"]=zscore(merged["z_return_A"])
    merged["z_return_B"]=zscore(merged["z_return_B"])
    corr=merged["z_return_A"].corr(merged["z_return_B"])
    return (merged.shape[0],corr)

def volume_trend(c:pd.DataFrame):
    import matplotlib.pyplot as plt
    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax2=ax1.twinx()
    ax1.plot(c["time"],c["close"], 'g-', label='return')
    ax2.plot(c["time"],c["volume"], 'b-', label='underlying')
    # ax2.plot(merged["time"],merged["residual_z"], 'b-', label='z')
    ax1.set_ylabel('trend', color='g')
    ax2.set_ylabel('underlying volume', color='b')
    plt.show()
    
    #download data2 for a list and data for a single one
def zscore(series: pd.Series,adjust_option: bool=False,halffile:int=10) -> pd.Series:
    ewma_std = series.ewm(halflife=halffile, adjust=adjust_option).std()
    ewma_mean= series.ewm(halflife=halffile, adjust=adjust_option).mean()
    # 可选：将前30日EWMA波动率替换为滚动标准差
    res=(series - ewma_mean)/ ewma_std
    return res

def get_option_data(contract_code:str,period:str="1m",start_time:str="",end_time:str=""):
    import time
    xtdata.download_history_data(contract_code,period,start_time=start_time,end_time=end_time)
    xtdata.subscribe_quote(contract_code, period=period, start_time=start_time, end_time=end_time, callback=None)
    data=xtdata.get_market_data_ex([],[contract_code],period=period,start_time=start_time,end_time=end_time)
    time.sleep(1)
    d=data[contract_code]
    d["time"]=pd.to_datetime(d["time"],unit='ms')
    d["daily_average_volume"]=d["volume"].rolling(window=240).mean()
    return d