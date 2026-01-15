from pydcca import DCCA
import numpy as np

# 生成两个相关序列
np.random.seed(42)
x = np.random.randn(1000).cumsum()
y = 0.5 * x + np.random.randn(1000).cumsum()

# 初始化（1阶去趋势）
dcca = DCCA(order=1)

# 计算在尺度 n=50 下的 DCCA 相关系数
rho = dcca.compute(x, y, n=50)
print(f"ρ_DCCA(50) = {rho:.3f}")