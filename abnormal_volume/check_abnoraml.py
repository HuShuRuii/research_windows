import time
import sys
sys.path.append(r'C:/Users/HP/Desktop/research')
import pandas as pd
from collections import deque,defaultdict
from xtquant import xtdatacenter,xtdata
import math
from datetime import datetime
import re
xtdatacenter.set_token("4065054877ce5724155dbc5bcba200381ce5eb35")
xtdatacenter.set_data_home_dir(r"C:\data_xtdata")
xtdatacenter.init(start_local_service=False)
#xtdatacenter.init()
xtdatacenter.listen(port=(58610,58620))

# data->differnt data->buffer(deque)
#                 -> feature to maintain
UNDERLYING:list[str]=["ag00.SF","au00.SF","cu00.SF","ru00.SF","zn00.SF"]
INTERVAL=1
pattern_option = r'^([a-zA-Z]+)(\d+)[-]*([a-zA-Z]*)[-]*(\d+)\.([a-zA-Z]+)$'
pattern_contract = r'^([a-zA-Z]+)(\d+)\.([a-zA-Z]+)$'


def data_filter(data:dict)->dict:
    data_return=defaultdict(list)
    underlying_tick:dict={}
    for symbol,tick in data.items():
        match_option = re.match(pattern_option, symbol)
        match_contract = re.match(pattern_contract, symbol)
        if match_contract:
            contract_class = match_contract.group(1)
            underlying_tick[contract_class]=tick
        elif match_option:
            option_class = match_option.group(1)  
            #option_underlying
            option_strike= match_option.group(4)        #option_strike
            option_type= match_option.group(3)          #option_type
            data_return[option_class].append((option_type+option_strike,tick))
    return data_return,underlying_tick

#每一个品种存一个volumedetector
class VolumeAnomalyDetector:
    def __init__(self, window_size=100, threshold_sigma=2.0,underlying_asset='') -> None: 
        # we use strike as the key
        self.window =defaultdict(lambda: deque(maxlen=window_size)) # 存最近 N 笔 volume
        self.threshold_sigma = threshold_sigma
        # 可选：缓存 sum 和 sum_sq 以 O(1) 更新统计量
        self.sum_vol = defaultdict(int)
        self.sum_sq =  defaultdict(int)
        self.underlying_asset=underlying_asset
        self.volume_old=defaultdict(int)
        self.underlying_price=float
        self.otm_option_list=defaultdict(bool)
    
    def update_otm_option(self) -> None:
        for symbol ,_ in self.otm_option_list.items():
            strike=float(symbol[1:])
            if symbol[0]in ["C","c"]:
                if strike>=self.underlying_price*1.02:
                    self.otm_option_list[symbol]=True
                else :
                    self.otm_option_list[symbol]=False
            else :
                if strike<=self.underlying_price*0.98:
                    self.otm_option_list[symbol]=True
                else :
                    self.otm_option_list[symbol]=False
                    
    def update_underlying(self, tick) -> None:
        self.underlying_price=tick['lastPrice']
                       
    def update_market_data(self, data,warning_list) -> None:
        for symbol, tick  in data:
            # 如果时间戳是在开盘或者是闭盘的那一阵子的话我们就不考虑, 20231026 10:32:56.950
            t=tick['timetag']
            pattern=r'(\d{8} \d{2}:\d{2}:\d{2}\.\d{3})'
            match=re.match(pattern,t)
            if match:
                dt = datetime.strptime(t, "%Y%m%d %H:%M:%S.%f")
            else:
                dt=datetime.strptime(t, "%Y%m%d %H:%M:%S")
            minute = dt.minute
            hour=dt.hour
            if (hour==9 and minute<15) or (hour==11 and minute>30) or (hour==13 and minute<30) or (hour==15 and minute>0):
                continue
        
            if len(self.window[symbol]) == self.window[symbol].maxlen:
                old = self.window[symbol][0]
                self.sum_vol[symbol] -= old
                self.sum_sq[symbol] -= old * old
            if symbol not in self.volume_old:
                self.volume_old[symbol]=tick["volume"]
                continue
            else :
                volume=tick["volume"]-self.volume_old[symbol]
                self.volume_old[symbol]=tick["volume"]
            # 添加新值
            self.window[symbol].append(volume)
            self.sum_vol[symbol]=self.sum_vol[symbol]+volume
            self.sum_sq[symbol]=self.sum_sq[symbol] +volume * volume

            # 计算均值和标准差
            n = len(self.window[symbol])
            if n < 10:  # 数据太少，不判断
                continue

            mean = self.sum_vol[symbol] / n
            variance = (self.sum_sq[symbol] / n) - (mean ** 2)
            std = math.sqrt(max(variance, 0))

            # 判断是否异常
            if std == 0:
               continue 
            z_score = (volume - mean) / std
            print(f"Option: {self.underlying_asset+symbol}, Volume: {volume}, Mean: {mean:.2f}, Std: {std:.2f}, Z-Score: {z_score:.2f}")
            if  z_score > self.threshold_sigma and self.otm_option_list[symbol]:
                warning_list.append((self.underlying_asset+symbol))
      
      
def get_option_list(underlying)->list[str]:
    option_list=[]
    try:
        for commodity_code in underlying:
            main_contract=xtdata.get_main_contract(commodity_code)
            print(f"主力合约: {main_contract}")
            optionlist=xtdata.get_option_undl_data(main_contract)
            option_list=option_list+optionlist
            option_list.append(main_contract)
    except Exception as e:
        print(f"获取期权列表失败: {e}")
        return []
    try:
        for option_code in option_list:
            pass
            # xtdata.download_history_data(option_code,"1m", start_time='', end_time='')
            # xtdata.subscribe_quote(option_code, period='1m', start_time='', end_time='', count=0, callback=None)
        print("market data downloaded")
    except Exception as e:
        print(f"订阅期权数据失败: {e}")
        return []

    return option_list


def main():
    # data=create_T_frame()
    warning_list=[]
    option_list=get_option_list(UNDERLYING)
    print(option_list)
    print("the option list is read")
    Detector=defaultdict(VolumeAnomalyDetector)
    next_time=INTERVAL+time.monotonic()
    print("the program start to run in cycle")
    while True:
        try:
            warning_list=[]
            d=xtdata.get_full_tick(option_list)
            d1,d2=data_filter(d)
            for contract_symbol, tick in d2.items():
                if contract_symbol not in Detector:
                    Detector[contract_symbol]=VolumeAnomalyDetector(window_size=100,threshold_sigma=3.0,underlying_asset=contract_symbol)
                Detector[contract_symbol].update_underlying(tick)
                Detector[contract_symbol].update_otm_option()
            for underlying_symbol, option_info in d1.items():
                Detector[underlying_symbol].update_market_data(option_info,warning_list)
            if len(warning_list)==0:
                print("No warning list")
            for warning in warning_list:
                print(f"检测到异常交易量的期权合约: {warning} 时间: {pd.Timestamp.now()}")
            
            current_time=time.monotonic()
            sleep_time=next_time-current_time
            if sleep_time>0:
                time.sleep(sleep_time)
            elif sleep_time<0:
                print(f"数据处理超时, 超过 {INTERVAL} 秒")
            next_time+=INTERVAL
            
        except KeyboardInterrupt:
            print("The program is interrupted by user.")
            time.sleep(1)
            return 
    
    
if __name__=="__main__":
    main()
    
    