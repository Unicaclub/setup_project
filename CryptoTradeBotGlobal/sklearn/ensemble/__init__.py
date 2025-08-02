# Stubs para classificadores e regressão do sklearn.ensemble
__all__ = [
    'RandomForestClassifier',
    'GradientBoostingClassifier',
    'RandomForestRegressor',
    'GradientBoostingRegressor'
]

class RandomForestClassifier:
    def __init__(self, *args, **kwargs):
        pass
    def fit(self, X, y):
        return self
    def predict(self, X):
        return [0 for _ in range(len(X))]

class GradientBoostingClassifier:
    def __init__(self, *args, **kwargs):
        pass
    def fit(self, X, y):
        return self
    def predict(self, X):
        return [0 for _ in range(len(X))]

class RandomForestRegressor:
    def __init__(self, *args, **kwargs):
        pass
    def fit(self, X, y):
        return self
    def predict(self, X):
        return [0.0 for _ in range(len(X))]

class GradientBoostingRegressor:
    def __init__(self, *args, **kwargs):
        pass
    def fit(self, X, y):
        return self
    def predict(self, X):
        return [0.0 for _ in range(len(X))]
