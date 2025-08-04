"""
Script para exportação de relatórios (PDF, JSON, CSV) do CryptoLogger Pro
"""

from reporting.relatorio_regulatorio import gerar_relatorio
import argparse
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exportar relatório regulatório.")
    parser.add_argument("--formato", choices=["pdf", "json", "csv"], default="json", help="Formato de exportação")
    parser.add_argument("--saida", default="./relatorio_exportado", help="Caminho do arquivo de saída (sem extensão)")
    args = parser.parse_args()

    relatorio = gerar_relatorio()
    saida = args.saida + "." + args.formato
    # Garante que o diretório existe
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    if args.formato == "json":
        with open(saida, "w", encoding="utf-8") as f:
            import json
            json.dump(relatorio, f, ensure_ascii=False, indent=2)
    elif args.formato == "csv":
        import csv
        with open(saida, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=relatorio[0].keys())
            writer.writeheader()
            writer.writerows(relatorio)
    elif args.formato == "pdf":
        try:
            from fpdf import FPDF
        except ImportError:
            print("Instale a biblioteca fpdf para exportar em PDF: pip install fpdf")
            exit(1)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for item in relatorio:
            for k, v in item.items():
                pdf.cell(0, 10, f"{k}: {v}", ln=1)
            pdf.cell(0, 10, "-"*40, ln=1)
        pdf.output(saida)
    print(f"Relatório exportado para {saida}")
