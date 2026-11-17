"""Download opcional do dataset do Kaggle em data/raw (requer `pip install kagglehub`).

NÃO TESTADO pelos autores; se falhar, siga as instruções manuais de data/raw/README.md.
"""
import glob
import os
import shutil

SLUG = "equeiroz/acidentes-rodovias-federais-brasil-jan07-a-jul19"


def main() -> None:
    try:
        import kagglehub
    except ImportError:
        raise SystemExit("Instale com `pip install kagglehub` ou baixe manualmente (data/raw/README.md).")
    origem = kagglehub.dataset_download(SLUG)
    os.makedirs("data/raw", exist_ok=True)
    for arq in glob.glob(os.path.join(origem, "**", "datatran*.csv"), recursive=True):
        shutil.copy(arq, "data/raw")
    print("Arquivos copiados para data/raw/")


if __name__ == "__main__":
    main()
