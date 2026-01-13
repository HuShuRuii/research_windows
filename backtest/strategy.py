import pandas as pd
import numpy as np
import type_declare

class Strategy:
    def __init__(self,name:str,window:int=20):
        self.name=name
        self.window=window
        
    def generate_signals(self,data:pd.DataFrame)->pd.Series:
        raise NotImplementedError("Should implement generate_signals()!")
