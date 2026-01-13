import pandas as pd
import numpy as np
import time
import re
import os
from datetime import datetime, timedelta
import sys
from xtquant import xtdata, xtdatacenter
xtdatacenter.set_token("4065054877ce5724155dbc5bcba200381ce5eb35")
xtdatacenter.set_data_home_dir(r"C:\data_xtdata")
xtdatacenter.init(start_local_service=False)
#xtdatacenter.init()
xtdatacenter.listen(port=(58610,58620))

trading_dates_path = 'trading_calendar.pkl'
trading_dates_df = pd.read_pickle(trading_dates_path)
trading_dates_list = trading_dates_df.iloc[:, 0].astype(str).tolist()

def get_market_data_origin(codes, period, start_time, end_time, count):
  
    for code in codes:
        xtdata.download_history_data(code, period, start_time, end_time)
        print(f'{code}的xtdata行情数据已下载')
    # xtdata.subscribe_quote(codes[0], period, start_time, end_time)
    market_data = xtdata.get_market_data_ex(
        [],
        codes,
        period,
        start_time,
        end_time,
        count=count,
        dividend_type="none",
        fill_data=False,
    )
    print(market_data)
    return market_data

def get_market_data(codes: list, period: str, start_time: str, end_time: str, count: int, download_mode = True) -> dict:
    """获取市场数据"""
    # 如果start_time或end_time为datetime对象，转换xtdata需要的字符串格式
    if isinstance(start_time, datetime) and isinstance(end_time, datetime):
        start_time = start_time.strftime('%Y%m%d')
        end_time = end_time.strftime('%Y%m%d')

    # 如果start_time或end_time为14位字符串，将对应日期的对应频率数据都下载再获取比较安全
    if len(start_time) == len(end_time) == 14 :
        start_date = start_time[:8]
        end_date = end_time[:8]
        if download_mode:
            for code in codes:
                xtdata.subscribe_quote(code, period, start_date, end_date, count, callback=None)
                xtdata.download_history_data(code, period, start_date, end_date)
                print(f'{code}的xtdata行情数据已下载')
        market_data = xtdata.get_market_data_ex([], codes, period, start_time, end_time, count=count, 
                                    dividend_type='none', fill_data=False)
    elif len(start_time) == len(end_time) == 8 and period in ['1m','5m','tick','10m','15m','30m','1h']:
        # 下列操作是为了获取离start_time和end_time最近的交易日
        # 同时为了考虑到夜盘，取到start_time的前一个交易日，以合成完整数据
        greater_than_target = trading_dates_df[trading_dates_df[0] >= start_time]
        start_trading_date = greater_than_target[0].min()  # 最近的大于 target 的值
        start_idx = trading_dates_df[trading_dates_df[0] == start_trading_date].index[0]
        start_trading_last_date = trading_dates_df.iloc[start_idx - 1, 0] if start_idx > 0 else None

        less_than_target = trading_dates_df[trading_dates_df[0] <= end_time]
        end_trading_date = less_than_target[0].max()  # 最近的小于 target 的值
        
        if download_mode:
            for code in codes:
                xtdata.subscribe_quote(code, period, start_trading_last_date, end_trading_date, count, callback=None)
                xtdata.download_history_data(code, period, start_trading_last_date, end_trading_date)
                print(f'{code}的xtdata行情数据已下载')
        market_data = xtdata.get_market_data_ex([], codes, period, start_trading_last_date, end_trading_date, count=count, 
                                    dividend_type='none', fill_data=False)
        for code in codes:
            if market_data[code].empty:
                print(f"{code} 数据获取失败！")
                break

            if market_data[code].index[-1][:8] != end_trading_date or market_data[code].index[0][:8] != start_trading_last_date:
                print(f"起始日期{market_data[code].index[0][:8]}，终止日期{market_data[code].index[-1][:8]},{code} 数据获取可能不完整！")

            # 时间过滤窗口（含夜盘）
            open_time = start_trading_last_date + '210000'  # 夜盘开始（无夜盘品种同样适用）
            close_time = end_trading_date + '150000'        # 收盘时间

            idx = market_data[code].index
            mask = (idx >= open_time) & (idx <= close_time)
            if not mask.any():
                market_data[code] = market_data[code].iloc[0:0]
                continue

            df_slice = market_data[code][mask].copy()
            # 处理异常时间段
            bad_suffix = ('090000', '085600', '085700', '085800', '085900')
            df_slice = df_slice[~df_slice.index.str.endswith(bad_suffix)]
            market_data[code] = df_slice
    # 剩下的情况是，输入的start_time和end_time都是8位字符串，且period是week，month级别，这种时候download要设置period = '1d'
    else: 
        if download_mode:
            for code in codes:
                xtdata.subscribe_quote(code, period, start_time, end_time, count, callback=None)
                xtdata.download_history_data(code, '1d', start_time, end_time)
                print(f'{code}的xtdata行情数据已下载')
        market_data = xtdata.get_market_data_ex([], codes, period, start_time, end_time, count=count, 
                                    dividend_type='none', fill_data=False)
    
    return market_data


def get_latest_price(code):
    today = time.strftime("%Y%m%d")
    data = get_market_data([code], "1m", today, today, 1)
    if code in data and not data[code].empty:
        return data[code]["close"].iloc[-1]
    else:
        return None


def get_expire_time(code: str, today=datetime.now().strftime("%Y%m%d"), is_date=0):
    '''计算到期时间'''
    detail_data = xtdata.get_instrument_detail(code)
    if detail_data == None:
        raise ValueError(f"{code}: 无法获取信息")
    else:
        expire_date = detail_data['ExpireDate']
        days_to_expiration = (datetime.strptime(expire_date, '%Y%m%d') - datetime.strptime(today, '%Y%m%d')).days
        if days_to_expiration <= 0:
            # logger.warning(f"{code}: T值非正，即将或已到期")
            days_to_expiration = 0.5
        if is_date:
            return expire_date, days_to_expiration
        else:
            return days_to_expiration
        

def get_multiplier(code: str):
    '''计算合约乘数'''
    detail_data = xtdata.get_instrument_detail(code)
    multiplier = detail_data['VolumeMultiple']
    
    return multiplier



def get_class_name(code: str):
    '''获取品种名称'''
    detail_data = xtdata.get_instrument_detail(code)
    class_name = detail_data['ProductName']
    if '期权' in class_name:
        class_name = class_name[:-2]
    
    return class_name


def get_option_code(code: str):
    ''' 'ag2508.SF' -> 获取标的对应期权代码(Series)'''
    code_prefix = code.split(".")[0]
    market = code.split(".")[1]
    opt_list = xtdata.get_stock_list_in_sector(market)

    opt_list = [opt for opt in opt_list if len(opt) > 11 and opt.startswith(code_prefix)
                and 'MSC' not in opt and 'MSP' not in opt]
    opt_list = pd.Series(opt_list)
    
    return opt_list

def get_option_list(market,data_type = 0):
    '''
    ToDo:取出指定market的期权合约

    Args:
        market: 目标市场，比如中金所填 IF 

    data_type: 返回数据范围，可返回已退市合约，默认仅返回当前

        0: 仅当前
        1: 仅历史
        2: 历史 + 当前
    '''
    if data_type != 0:
        xtdata.download_history_contracts()
    _history_sector_dict = {
        "IF":"过期中金所",
        "SF":"过期上期所",
        "DF":"过期大商所",
        "ZF":"过期郑商所",
        'GF':"过期广期所",
        "INE":"过期能源中心",
        "SHO":"过期上证期权",
        "SZO":"过期深证期权",
    }

    # _now_secotr_dict = {
    #     "IF":"中金所",
    #     "SF":"上期所", aaa
    #     "DF":"大商所", AAA
    #     "ZF":"郑商所",
    #     'GF':"广期所",
    #     "INE":"能源中心",
    #     "SHO":"上证期权",
    #     "SZO":"深证期权",
    # }
   
    _sector = _history_sector_dict.get(market)
    # _now_sector = _now_secotr_dict.get(market)
    if _sector == None:
        raise KeyError(f"不存在该市场:{market}")
    _now_sector = _sector[2:]
    
    
    # 过期上证和过期深证有专门的板块，不需要处理
    if market == "SHO" or market == "SZO":
        if data_type == 0:
            _list = xtdata.get_stock_list_in_sector(_now_sector)
        elif data_type == 1:
            _list = xtdata.get_stock_list_in_sector(_sector)
        elif data_type == 2:
            _list = xtdata.get_stock_list_in_sector(_sector) + xtdata.get_stock_list_in_sector(_now_sector)
        else:
            raise KeyError(f"data_type参数错误:{data_type}")
        return _list
        
    # 期货期权需要额外处理
    if data_type == 0:
        all_list = xtdata.get_stock_list_in_sector(_now_sector)
    elif data_type == 1:
        all_list = xtdata.get_stock_list_in_sector(_sector)
    elif data_type == 2:
        all_list = xtdata.get_stock_list_in_sector(_sector) + xtdata.get_stock_list_in_sector(_now_sector)
    else:
        raise KeyError(f"data_type参数错误:{data_type}")
    
    _list = []
    pattern1 = r'^[A-Z]{2}\d{4}-[A-Z]-\d{4}\.[A-Z]+$'
    pattern2 = r'^[a-zA-Z]+\d+[a-zA-Z]\d+\.[A-Z]+$'
    pattern3 = r'^[a-zA-Z]+\d+-[a-zA-Z]-\d+\.[A-Z]+$'
    
    for i in all_list:
        if re.match(pattern1,i):
            _list.append(i)
        elif re.match(pattern2,i):
            _list.append(i)
        elif re.match(pattern3,i):
            _list.append(i)
    # _list =[i for i in all_list if re.match(pattern, i)]
    
    return _list


def get_contract_data(contract_code:str,period:str="1m",start_time:str="",end_time:str=""):
    xtdata.download_history_data(contract_code,period,start_time=start_time,end_time=end_time)
    xtdata.subscribe_quote(contract_code, period=period, start_time=start_time, end_time=end_time, callback=None)
    data=xtdata.get_market_data_ex([],[contract_code],period=period,start_time=start_time,end_time=end_time)
    time.sleep(1)
    d=data[contract_code]
    d["time"]=pd.to_datetime(d["time"],unit='ms')
    return d

def get_option_data(contract_code:str,period:str="1m",start_time:str="",end_time:str=""):
    xtdata.download_history_data(contract_code,period,start_time=start_time,end_time=end_time)
    xtdata.subscribe_quote(contract_code, period=period, start_time=start_time, end_time=end_time, callback=None)
    data=xtdata.get_market_data_ex([],[contract_code],period=period,start_time=start_time,end_time=end_time)
    time.sleep(1)
    d=data[contract_code]
    d["time"]=pd.to_datetime(d["time"],unit='ms')
    return d