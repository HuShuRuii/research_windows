import pickle
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def f(x):
    return x * x
if __name__ == '__main__':
    data=[1,2,3,4,5]
    with ThreadPoolExecutor(max_workers=6) as executor:
        result=list(executor.map(f,data))
    print(result)