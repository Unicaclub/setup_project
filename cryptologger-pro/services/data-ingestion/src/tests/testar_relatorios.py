"""
Testes para relatórios e auditoria.
"""
from ..reporting.relatorio_regulatorio import RelatorioRegulatorio
from ..reporting.log_auditoria import LogAuditoria

def test_exportar_json(tmp_path):
    rel = RelatorioRegulatorio()
    dados = [{"a": 1, "b": 2}]
    caminho = tmp_path / "saida.json"
    rel.exportar_json(dados, str(caminho))
    assert caminho.exists()

def test_log_auditoria():
    log = LogAuditoria()
    log.registrar("teste", {"x": 1})
    assert log.exportar()
