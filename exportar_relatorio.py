import sys
sys.path.insert(0, './cryptologger-pro/services/data-ingestion/src')
from exportar_relatorio import *
if __name__ == "__main__":
    import runpy
    runpy.run_module('exportar_relatorio', run_name='__main__')
