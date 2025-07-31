from .base_exchange import BaseExchange

class BinanceAdapter(BaseExchange):
    def connect(self):
        # Implementar conexão com Binance
        pass

    def get_ticker(self):
        # Implementar obtenção de ticker
        pass

    def place_order(self):
        # Implementar colocação de ordem
        pass

    def get_orderbook(self):
        # Implementar obtenção de orderbook
        pass
