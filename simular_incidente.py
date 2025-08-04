import sys
sys.path.insert(0, './cryptologger-pro/services/data-ingestion/src')
from simular_incidente import *
if __name__ == "__main__":
    tipo = sys.argv[1] if len(sys.argv) > 1 else None
    simular(tipo)
