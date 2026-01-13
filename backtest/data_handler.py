import pandas as pd
import time
from type_declare import Period
from xtquant import xtdata,xtdatacenter
xtdatacenter.set_token("4065054877ce5724155dbc5bcba200381ce5eb35")
xtdatacenter.set_data_home_dir(r"C:\data_xtdata")
xtdatacenter.init(start_local_service=False)
#xtdatacenter.init()
xtdatacenter.listen(port=(58610,58620))

trading_dates_path = 'trading_calendar.pkl'
trading_dates_df = pd.read_pickle(trading_dates_path)
trading_dates_list = trading_dates_df.iloc[:, 0].astype(str).tolist()
class DataHandler:
    def __init__(self):
        pass
    
    def get_data(self,symbols:list[str],start:str="",end:str="",period:Period=Period.MINUTE)->pd.DataFrame:
        xtdata.download_history_data2(symbols,str(period),start_time=start,end_time=end)
        for symbol in symbols:
            xtdata.subscribe_quote(symbol, period=str(period), start_time=start, end_time=end, callback=None)
        data=xtdata.get_market_data_ex([],symbols,period=str(period),start_time=start,end_time=end)
        time.sleep(1)
        for symbol in symbols:
            data[symbol]["time"]=pd.todatetime(data[symbol]["time"],unit='ms')
        return data
