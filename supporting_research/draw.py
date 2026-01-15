import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
def draw_plot(dfs: list[pd.DataFrame], x: str = 'time', y: str = 'value'):
    if(len(dfs)==2):
        fig, ax1 = plt.subplots(figsize=(10, 4))
        ax2 = ax1.twinx()
        ax1.plot(dfs[0][x],dfs[0][y], 'g-', label='stock_1')
        ax2.plot(dfs[1][x], dfs[1][y], 'b-', label='stock_2')
        ax1.set_ylabel('DF close', color='g')
        ax2.set_ylabel('SF close', color='b')
        plt.show()
        return
    colors = plt.cm.tab10.colors 
    plt.figure(figsize=(12, 4))
    for i, df in enumerate(dfs):
        color = colors[i % len(colors)]
        plt.plot(df[x], df[y], color=color)
    plt.xlabel('time')
    plt.ylabel("price")
    plt.title('trend')
    plt.tight_layout()
    plt.show()

def draw_scatter(x:pd.Series,y:pd.Series,xlabel='X',ylabel='Y',title='Scatter Plot'):
    plt.figure(figsize=(8, 6))
    plt.scatter(x, y, alpha=0.7)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.show()
    
def draw_heatmap(df: pd.DataFrame, xlabel:str, ylabel:str,zlabel:str, title:str='Heatmap'):
    heatmap_data = df.pivot(
    index=xlabel,     
    columns=ylabel, 
    values=zlabel    
    )

    plt.figure(figsize=(10, 8))
    sns.heatmap(
        heatmap_data,
        annot=True,           # 显示数值
        fmt='.2%',            # 格式化为百分比
        cmap='RdYlGn',        # 红-黄-绿：红=低收益，绿=高收益
        cbar_kws={'label': 'Annual Return'}
    )

    plt.title('Strategy Annual Return over different Parameters', fontsize=14)
    plt.xlabel('Short Window')
    plt.ylabel('Long Window')
    plt.show()

def draw_simple(dfs:list[list[pd.Series]], x: str = 'time', y: str = 'value'):
    plt.figure(figsize=(12, 4))
    colors = plt.cm.tab10.colors 
    for i,df in enumerate(dfs):
        plt.plot(df[0], df[1], color=colors[i % len(colors)])
    plt.xlabel(x)
    plt.ylabel(y)
    plt.title('trend')
    plt.tight_layout()
    plt.show()