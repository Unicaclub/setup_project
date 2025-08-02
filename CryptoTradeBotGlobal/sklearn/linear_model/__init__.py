# Stubs para sklearn.linear_model
__all__ = [
    'LinearRegression',
    'Ridge'
]

class LinearRegression:
    def __init__(self, *args, **kwargs):
        pass
    def fit(self, X, y):
        return self
    def predict(self, X):
        return [0.0 for _ in range(len(X))]

class Ridge:
    def __init__(self, *args, **kwargs):
        pass
    def fit(self, X, y):
        return self
    def predict(self, X):
        return [0.0 for _ in range(len(X))]
