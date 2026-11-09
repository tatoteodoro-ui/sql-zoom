# -*- coding: utf-8 -*-
"""Testes da leitura do texto digitado (sql_zoom/entrada.py). Não precisa do QGIS.

Rodar na raiz do repositório:  python testes/test_entrada.py   (ou: pytest testes)
"""
import importlib.util
import os

_ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql_zoom", "entrada.py")
_spec = importlib.util.spec_from_file_location("entrada", _ARQ)
entrada = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(entrada)

B = entrada.Busca


def test_so_sq_vai_para_quadra():
    assert entrada.interpretar("001.002") == B("001", "002", None, None)
    assert entrada.interpretar("001002") == B("001", "002", None, None)
    assert entrada.interpretar("1.2") == B("001", "002", None, None)


def test_sql_sem_digito():
    assert entrada.interpretar("001.002.0003") == B("001", "002", "0003", None)
    assert entrada.interpretar("0010020003") == B("001", "002", "0003", None)
    assert entrada.interpretar("1.2.3") == B("001", "002", "0003", None)


def test_sql_com_digito():
    assert entrada.interpretar("001.002.0003-4") == B("001", "002", "0003", "4")
    assert entrada.interpretar("00100200034") == B("001", "002", "0003", "4")
    assert entrada.interpretar(" 001.002.0003-4 ") == B("001", "002", "0003", "4")


def test_formatos_invalidos():
    for t in ("", "   ", "abc", "1", "001.002.00034.5", "0010", "001.002.0003-45"):
        assert entrada.interpretar(t) is None, t


def test_descrever():
    assert entrada.descrever(entrada.interpretar("001.002")) == "Quadra 001.002"
    assert entrada.descrever(entrada.interpretar("1.2.3")) == "Lote 001.002.0003"
    assert entrada.descrever(entrada.interpretar("1.2.3-4")) == "Lote 001.002.0003-4"


def test_mesmo_numero():
    assert entrada.mesmo_numero("083", 83)
    assert entrada.mesmo_numero(83.0, "83")
    assert not entrada.mesmo_numero("083", "084")
    assert entrada.mesmo_numero("X", "X")


if __name__ == "__main__":
    for nome, f in sorted(globals().items()):
        if nome.startswith("test_") and callable(f):
            f()
            print("ok ", nome)
    print("Todos os testes passaram.")
