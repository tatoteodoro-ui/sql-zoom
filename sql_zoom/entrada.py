# -*- coding: utf-8 -*-
"""Interpretação do que foi digitado (Python puro, sem QGIS, para poder testar).

Aceita, com ou sem pontos, traço e espaços:
    001.002            -> só a quadra (SQ)
    001.002.0003       -> lote (SQL sem dígito)
    001.002.0003-4     -> lote com dígito verificador (o dígito é conferido)
    0010020003 / 00100200034 / 001002
Setor e quadra podem vir sem os zeros à esquerda quando separados por ponto (1.2.3 = 001.002.0003).
"""
import re
from collections import namedtuple

Busca = namedtuple("Busca", "setor quadra lote digito")
# setor e quadra: 3 dígitos; lote: 4 dígitos; digito: 1 dígito. lote/digito = None quando não informados.

_COM_SEPARADOR = re.compile(r"^(\d{1,3})\.(\d{1,3})(?:\.(\d{1,4})(?:-(\d))?)?$")
_SO_DIGITOS = re.compile(r"^(\d{3})(\d{3})(?:(\d{4})(\d)?)?$")


def interpretar(texto):
    """Devolve uma Busca ou None se o texto não for um SQ/SQL válido."""
    t = re.sub(r"\s+", "", texto or "")
    t = t.replace(",", ".").replace("/", ".")
    m = _COM_SEPARADOR.match(t) or _SO_DIGITOS.match(t.replace(".", "").replace("-", ""))
    if not m:
        return None
    setor, quadra, lote, digito = m.groups()
    return Busca(setor.zfill(3), quadra.zfill(3),
                 lote.zfill(4) if lote else None,
                 digito if digito else None)


def sq_texto(b):
    return "%s.%s" % (b.setor, b.quadra)


def descrever(b):
    """Texto curto para a tela e para as mensagens."""
    if b.lote is None:
        return "Quadra %s" % sq_texto(b)
    s = "Lote %s.%s" % (sq_texto(b), b.lote)
    return s + ("-%s" % b.digito if b.digito else "")


def mesmo_numero(a, b):
    """Compara códigos que podem vir como texto ('083') ou número (83)."""
    try:
        return int(float(str(a).strip())) == int(float(str(b).strip()))
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()
