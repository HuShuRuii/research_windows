from .type_declare import Period
import pandas as pd
import numpy as np
class PerformanceSummary:
    def __init__(self,history:pd.DataFrame,interest_rate:float=0.0):
        self.history=history
        self.interest_rate=interest_rate
        self.period=history.index.to_series().diff().mode()[0]
        self.periods_per_year=self.periods_per_year()
        self.returns=self.annualized_return()
        self.drawdowns=self.max_drawdown()
        self.sharpes=self.sharpe_ratio()
        self.calmar_ratios=self.calmar_ratio()
        self.volatilities=self.return_volatility()
        self.performance={
            "returns": self.returns,
            "drawdowns": self.drawdowns,
            "sharpes": self.sharpes,
            "calmar_ratios": self.calmar_ratios,
            "volatilities": self.volatilities
        }

    def performance_as_dict(self):
        return self.performance

    def periods_per_year(self)->int:
        if self.period >= pd.Timedelta(days=365):
            return 1
        elif self.period >= pd.Timedelta(weeks=52):
            return 52
        elif self.period == pd.Timedelta(days=1):
            return 252
        elif self.period >= pd.Timedelta(hours=1):
            return 252 * 6.5
        elif self.period >= pd.Timedelta(minutes=1):
            return 252 * 6.5 * 60
        else:
            return 252 * 6.5 * 60 * 60 # seconds
    
    def max_drawdown(self)->float:
        rolling_max = self.history.cummax()
        drawdowns = (self.history - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        return max_drawdown

    def annualized_return(self)->float:
        periods_per_year=self.periods
        total_return = self.history.iloc[-1] / self.history.iloc[0] - 1
        num_years = len(self.history) / periods_per_year
        annualized_return = (1 + total_return) ** (1 / num_years) - 1
        return annualized_return

    def return_volatility(self)->float:
        returns = self.history.pct_change().dropna()
        annualized_volatility = returns.std() * np.sqrt(self.periods_per_year)
        return annualized_volatility

    def return_simple(self)->float:
        total_return = self.history.iloc[-1] / self.history.iloc[0] - 1
        return total_return

    def sharpe_ratio(self)->float:
        returns = self.history.pct_change().dropna()
        excess_returns = returns - (self.risk_free_rate / self.periods_per_year)
        annualized_return = excess_returns.mean() *self.periods_per_year
        annualized_volatility = excess_returns.std() * np.sqrt(self.periods_per_year)
        if annualized_volatility == 0:
            return np.nan
        sharpe_ratio = annualized_return / annualized_volatility
        return sharpe_ratio

    def calmar_ratio(self)->float:
        total_return = self.history.iloc[-1] / self.history.iloc[0] - 1
        num_years = len(self.history) / self.periods_per_year
        annualized_return = (1 + total_return) ** (1 / num_years) - 1
        max_dd = abs(self.max_drawdown(self.history))
        if max_dd == 0:
            return np.nan
        calmar_ratio = annualized_return / max_dd
        return calmar_ratio