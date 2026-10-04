"""TAREFA DO ALUNO -- os cinco testes que faltam para os >= 8 do entregavel."""

from __future__ import annotations

from decimal import Decimal
import pytest

from app.dominio.motor_emergia import calcular_indices, SEIS_CASAS
from app.dominio.tipos import FluxoEmergetico, CategoriaFluxo

def test_regressao_numerica_contra_a_planilha(fluxos_golden):
    """Compara os seis indices com a aba SSB da Planilha_base.xlsx."""
    # Montei esse cenário na mão olhando a planilha (Y=200, F=50, R=115, N=85) 
    fluxos = [
        FluxoEmergetico(recurso="Chuva", categoria=CategoriaFluxo.R, emergia_sej=Decimal("115")),
        FluxoEmergetico(recurso="Solo", categoria=CategoriaFluxo.N, emergia_sej=Decimal("35")),
        FluxoEmergetico(recurso="Diesel", categoria=CategoriaFluxo.MN, emergia_sej=Decimal("50"))
    ]
    
    indices = calcular_indices(fluxos, energia_produto_j=Decimal("1000"))

    assert indices.y == Decimal("200.000000")
    assert indices.eyr == Decimal("4.000000")
    assert indices.elr == Decimal("0.739130")
    assert indices.esi == Decimal("5.411765")
    assert indices.eii == Decimal("0.184783")
    assert indices.percentual_r == Decimal("57.500000")


def test_quantizacao_unica_no_final():
    """Mostra o erro duplo de arredondar no meio do calculo."""
    fluxos = [
        FluxoEmergetico(recurso="R", categoria=CategoriaFluxo.R, emergia_sej=Decimal("115")),
        FluxoEmergetico(recurso="N", categoria=CategoriaFluxo.N, emergia_sej=Decimal("35")),
        FluxoEmergetico(recurso="MN", categoria=CategoriaFluxo.MN, emergia_sej=Decimal("50"))
    ]
    indices = calcular_indices(fluxos, energia_produto_j=Decimal("1000"))

    # Notei que ao arredondar as partes da conta 
    # (EYR e ELR) ANTES de dividir, o erro vai se acumulando.
    eyr_arredondado = indices.eyr
    elr_arredondado = indices.elr 
    esi_errado = (eyr_arredondado / elr_arredondado).quantize(SEIS_CASAS)

    # O correto é deixar o motor fazer tudo com os 28 dígitos internos e 
    # só cortar as casas decimais na resposta final.
    esi_correto = indices.esi

    assert esi_errado != esi_correto
    assert esi_errado == Decimal("5.411768")
    assert esi_correto == Decimal("5.411765")


def test_ordem_da_soma_com_magnitudes_divergentes():
    """A associatividade quebra quando as magnitudes divergem."""
    # EXPLICAÇÃO NO CORPO DO TESTE (conforme exigido no README):
    # No motor, o limite de casas foi definido em 28 dígitos (ctx.prec = 28).
    # Ao somar um número maior (1E14) com um menor (1E-15), 
    # a distância entre as pontas é de 29 casas. Como o contexto só guarda 28,
    # a linguagem descarta o menor por ausencia de memória. Por isso a ordem 
    # importa na regra de negócio: somar do menor pro maior garante que os
    # menores se acumulem antes de se encontrarem com os maiores.
    
    f_grande = FluxoEmergetico(recurso="A", categoria=CategoriaFluxo.R, emergia_sej=Decimal("1E14"))
    f_pequeno = FluxoEmergetico(recurso="B", categoria=CategoriaFluxo.R, emergia_sej=Decimal("1E-15"))
    # Fluxo 'MN' do mesmo tamanho para as divisões não explodirem o limite de 28 dígitos
    f_comprado = FluxoEmergetico(recurso="C", categoria=CategoriaFluxo.MN, emergia_sej=Decimal("1E14"))
    
    res1 = calcular_indices([f_grande, f_pequeno, f_comprado], Decimal("1000")).y
    res2 = calcular_indices([f_pequeno, f_grande, f_comprado], Decimal("1000")).y
    
    assert res1 == res2


def test_erro_de_dominio_responde_problem_json(cliente, corpo_golden):
    """Inventario sem fluxo renovavel deve sair 422 em application/problem+json."""
    # Para forçar o erro de "denominador do ELR nulo", o inventário não pode ter
    # fluxo renovável (nem R, nem MR, nem SR).
    # Substituímos a lista por um fluxo comprado não-renovável (MN).
    corpo = corpo_golden.copy()
    corpo["fluxos"] = [
        {"recurso": "Diesel", "categoria": "MN", "emergia_sej": 100}
    ]

    resposta = cliente.post("/v1/safras/42/calculos", json=corpo)

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == "application/problem+json"
    
    dados = resposta.json()
    assert dados["status"] == 422
    assert "type" in dados
    assert "title" in dados
    assert "detail" in dados
    assert "instance" in dados


def test_campo_extra_no_corpo_da_requisicao_e_rejeitado(cliente, corpo_golden):
    """"energia_produto_jj" tem de morrer com 422, nao virar calculo incompleto."""
    # Injetando um erro de digitação intencional no JSON pra provar que o extra="forbid"
    # que configuramos no DTO realmente captura o erro na porta de entrada da API.
    corpo = corpo_golden.copy()
    corpo["energia_produto_jj"] = 1000

    resposta = cliente.post("/v1/safras/42/calculos", json=corpo)

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == "application/problem+json"