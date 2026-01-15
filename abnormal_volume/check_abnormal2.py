import time
import sys
sys.path.append(r'C:/Users/HP/Desktop/research')
import pandas as pd
from collections import deque,defaultdict
from xtquant import xtdatacenter,xtdata
import math,statistics,re
from datetime import datetime,timedelta

xtdatacenter.set_token("4065054877ce5724155dbc5bcba200381ce5eb35")
xtdatacenter.set_data_home_dir(r"C:\data_xtdata")
xtdatacenter.init(start_local_service=False)
#xtdatacenter.init()
xtdatacenter.listen(port=(58610,58620))

UNDERLYING:list[str]=["ag00.SF","au00.SF","cu00.SF","ru00.SF","zn00.SF"]
INTERVAL=5  #seconds
PAST_DAYS=5


def tick_time(t)->str:
        pattern=r'(\d{8} \d{2}:\d{2}:\d{2}\.\d{3})'
        match=re.match(pattern,t)
        if match:
            dt = datetime.strptime(t, "%Y%m%d %H:%M:%S.%f")
        else:
            dt= datetime.strptime(t, "%Y%m%d %H:%M:%S")
        minute = dt.minute
        hour=dt.hour
        return f"{hour}:{minute}"

def read_option_strike_type(symbol:str)->tuple:
    pattern_option = r'^([a-zA-Z]+)(\d+)[-]*([a-zA-Z]*)[-]*(\d+)\.([a-zA-Z]+)$'
    match_option = re.match(pattern_option, symbol)
    if match_option:
        option_strike= match_option.group(4)        #option_strike
        option_type= match_option.group(3)          #option_type
        return option_strike,option_type
    else:
        return None,None

def get_option_info(symbol:str):
    pattern_option = r'^([a-zA-Z]+)(\d+)[-]*([a-zA-Z]*)[-]*(\d+)\.([a-zA-Z]+)$'
    match_option = re.match(pattern_option, symbol)
    if match_option:
        option_class = match_option.group(1)  
        option_strike= match_option.group(4)        #option_strike
        option_type= match_option.group(3)          #option_type
        return option_class,option_type+option_strike
    else:
        return None,None
    
def data_filter(data:dict)->dict:
    data_return=defaultdict(list)
    underlying_tick:dict={}
    pattern_option = r'^([a-zA-Z]+)(\d+)[-]*([a-zA-Z]*)[-]*(\d+)\.([a-zA-Z]+)$'
    pattern_contract = r'^([a-zA-Z]+)(\d+)\.([a-zA-Z]+)$'
    for symbol,tick in data.items():
        match_option = re.match(pattern_option, symbol)
        match_contract = re.match(pattern_contract, symbol)
        if match_contract:
            contract_class = match_contract.group(1)
            underlying_tick[contract_class]=tick
        elif match_option:
            option_class = match_option.group(1)  
            option_strike= match_option.group(4)        #option_strike
            option_type= match_option.group(3)          #option_type
            data_return[option_class].append((option_class,option_type+option_strike,tick))
    return data_return,underlying_tick

def z_score (volume:int,volume_list:list)->float:
    mean=statistics.mean(volume_list)
    std=statistics.stdev(volume_list)
    if std==0:
        return None
    z_score = (volume -mean) / std
    return z_score

#每一个品种存一个volumedetector
class VolumeAnomalyDetector:
    def __init__(self, threshold_sigma=2.0,underlying_asset='') -> None: 
        # we use strike as the key
        self.threshold_sigma = threshold_sigma
        self.underlying_asset=underlying_asset
        self.volume_old=defaultdict(int)
        self.underlying_price=float
        self.otm_option_list=defaultdict(bool)
        self.pastdata_volume_avg=defaultdict(lambda:dict)
        self.pastdata_volume_std=defaultdict(lambda:dict)
        # self.pastdata_volume=defaultdict(lambda:defaultdict(list))
    
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

            if symbol not in self.volume_old:
                self.volume_old[symbol]=tick['volume']
                continue
            volume=tick['volume']-self.volume_old[symbol]
            self.volume_old[symbol]=tick['volume']
            # store past volume data
            
            z_score = (volume -self.pastdata_volume_avg.get(symbol,0)) / self.pastdata_volume_std.get(symbol,1)
            # print(f"Option: {self.underlying_asset+symbol}, Volume: {volume}, Mean: {mean:.2f}, Std: {std:.2f}, Z-Score: {z_score:.2f}")
            if  z_score > self.threshold_sigma and self.otm_option_list[symbol]:
                warning_list.append((self.underlying_asset+symbol))
      
def extract_hour_minute_with_offset(ts):
    dt = datetime.fromtimestamp(ts / 1000)
    dt += timedelta(hours=8)
    return f"{dt.hour}:{dt.minute}"

    
def get_list(underlying):
    option_list=[]
    contract_list=[]
    try:
        for commodity_code in underlying:
            main_contract=xtdata.get_main_contract(commodity_code)
            print(f"主力合约: {main_contract}")
            optionlist=xtdata.get_option_undl_data(main_contract)
            option_list=option_list+optionlist
            contract_list.append(main_contract)
    except Exception as e:
        print(f"获取期权列表失败: {e}")
        return []
    return option_list,contract_list

def process_history_data(option_list,Detector):
    now_day = pd.Timestamp.now()
    previous_day = now_day - pd.Timedelta(days=PAST_DAYS)
    str_t = lambda t: t.strftime("%Y%m%d")
    try:
        xtdata.download_history_data2(option_list,"1m", start_time=str_t(previous_day), end_time=str_t(now_day))
        print("market data downloaded")
        data_option=xtdata.get_market_data(field_list=["volume"],stock_list=option_list,start_time=str_t(previous_day),end_time=str_t(now_day))
        for option_code in option_list:
            pd=data_option[option_code]
            pd["volume_"]=pd['voume'].diff().dropna()
            print(pd["time"])
            pd["time"]=pd['time'].apply(extract_hour_minute_with_offset)
            option_class, symbol =get_option_info(option_code)
            if option_class not in Detector:
                Detector[option_class]=VolumeAnomalyDetector(threshold_sigma=3.0,underlying_asset=option_class)
            volume_avg=pd.pivot_table(pd,values='volume_',index='time',aggfunc='mean').to_dict()
            volume_std=pd.pivot_table(pd,values='volume_',index='time',aggfunc='std').to_dict()
            Detector[option_class].pastdata_volume_avg[symbol].update(volume_avg)
            Detector[option_class].pastdata_volume_std[symbol].update(volume_std)
                
    except Exception as e:
        print(f"订阅期权数据失败: {e}")
        return []
    
def main():
    # data=create_T_frame()
    Detector=defaultdict(lambda: VolumeAnomalyDetector())
    option_list,contract_list=get_list(UNDERLYING)
    process_history_data(option_list,Detector)
    warning_list=[]
    
    next_time=INTERVAL+time.monotonic()
    print("the program start to run in cycle")
    while True:
        try:
            warning_list=[]
            data=xtdata.get_full_tick(contract_list)
            d1,d2=data_filter(d)
            for contract_symbol, tick in d2.items():
                if contract_symbol not in Detector:
                    Detector[contract_symbol]=VolumeAnomalyDetector(window_size=100,threshold_sigma=3.0,underlying_asset=contract_symbol)
                Detector[contract_symbol].update_underlying(tick)
                Detector[contract_symbol].update_otm_option()
            
            data=xtdata.get_full_tick(option_list)
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
    
    