# Stub mínimo para sklearn.ensemble
# Permite importações como: from sklearn.ensemble import RandomForestClassifier


# Stubs para classificadores
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

# Stubs para regressão
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
