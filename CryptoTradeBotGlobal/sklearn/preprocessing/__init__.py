# Stubs para sklearn.preprocessing
__all__ = [
    'StandardScaler',
    'MinMaxScaler'
]

class StandardScaler:
    def __init__(self, *args, **kwargs):
        pass
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        return X
    def fit_transform(self, X, y=None):
        return self.transform(X)

class MinMaxScaler:
    def __init__(self, *args, **kwargs):
        pass
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        return X
    def fit_transform(self, X, y=None):
        return self.transform(X)
