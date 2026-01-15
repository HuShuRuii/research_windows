import re
import pandas as pd
from read_xtdata_1 import get_option_list, get_class_name, get_multiplier, get_expire_time
from xtquant import xtdata,xtdatacenter
import time
from datetime import datetime, timedelta
from scipy import stats
xtdatacenter.set_token("4065054877ce5724155dbc5bcba200381ce5eb35")
xtdatacenter.set_data_home_dir(r"C:\data_xtdata")
xtdatacenter.init(start_local_service=False)
#xtdatacenter.init()
xtdatacenter.listen(port=(58610,58620))

UNDERLYING:list[str]=["ag00.SF"]
INTERVAL=60.0

def get_all_code_info(code):
    '''输入完整代码, 返回: code(不含市场), market, product(含市场), under(不含市场), option_type, K'''
    pattern = r'^([a-zA-Z]+)(\d+)[-]*([a-zA-Z]*)[-]*(\d+)\.([a-zA-Z]+)$'
    match = re.match(pattern, code)
    
    if match:
        option_class = match.group(1)        # 第一个字母组合
        month = match.group(2)      # 第一个数字组合
        option_type = match.group(3)    # 中间字母
        K = match.group(4)      # 第二个数字组合
        market = match.group(5)        # 后缀字母组合
        
        code = code.split('.')[0]
        product = option_class + '00.' + market
        under = option_class + month
        
        return pd.Series([code, market, product, under, option_type, float(K)])
    else:
        print(f'{code}：代码分割出信息时出现问题')
        return None
    
def create_T_frame(market_list=['ZF','DF','SF','GF','INE']):
    '''建立全市场期权链'''
    # 获取全市场期权
    all_option = []
    for market in market_list:
        all_option += get_option_list(market, data_type=0)
    df_option = pd.DataFrame(all_option, columns=['code'])
    df_option[['code', 'market', 'product', 'under', 'type', 'K']] = df_option['code'].apply(get_all_code_info)
    
    dict_report = {}
    
    # 交易所
    for market, df_market in df_option.groupby(['market']):
        market_code = market[0]

        # 品种
        for product, df_product in df_market.groupby(['product']):
            product_code = product[0]
            product_name = get_class_name(product_code)
            multiplier = get_multiplier(product_code)
            
            
            # 按合约分类
            for under, df_under in df_product.groupby(['under']):
                under_code = under[0]
                full_option_code = df_under['code'].iloc[0] + '.' + market_code
                expiry_date, days_to_expiration = get_expire_time(full_option_code, is_date=1)

                df_under = df_under.set_index('code')

                # 汇总
                dict_report[under_code] = {
                    'market': market_code,
                    'product': product_name,
                    'multiplier':multiplier, 
                    'expiry_date':expiry_date, 
                    'days_to_expiration':days_to_expiration,
                    'option_chain': df_under,
                    }
                
    return dict_report

def time_before_str(days:int,minutes:int=0,seconds:int=0)->str:
    time_pd=pd.Timestamp.now()
    delta=pd.Timedelta(days=days,minutes=minutes,seconds=seconds)
    new_time=time_pd-delta
    return new_time.strftime('%Y-%m-%d %H:%M:%S')
