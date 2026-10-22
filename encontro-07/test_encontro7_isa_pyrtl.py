"""Testes do contrato e exemplos; não é o gabarito de todas as extensões."""
import random
import pytest
import pyrtl
from encontro7_isa_pyrtl import (
    MOVI, MOV, LOAD, STORE, ADDI, INDEXADO, codificar, campos_ref, sinal8,
    montar_decodificador, montar_enderecador, endereco_ref, simular_carga,
)


def test_decodificador_todas_as_palavras():
    montar_decodificador()
    sim = pyrtl.FastSimulation(tracer=None)
    validas = 0
    for palavra in range(65536):
        esperado = campos_ref(palavra)
        sim.step({'instr': palavra})
        assert {n: sim.inspect(n) for n in esperado} == esperado
        validas += esperado['valido']
        if esperado['valido']:
            assert codificar(esperado['opcode'], esperado['rd'], esperado['base'],
                             sinal8(esperado['imm8'])) == palavra
    assert validas == 13328


@pytest.mark.parametrize('args', [(LOAD, 4, 2, 12), (LOAD, 1, 4, 12),
                                 (LOAD, 1, 2, 128), (LOAD, 1, 2, -129),
                                 (0, 0, 0, 0), (MOVI, 1, 1, 5), (MOV, 1, 2, 1)])
def test_rejeita_campos(args):
    with pytest.raises(ValueError):
        codificar(*args)


def test_extremos_imediatos():
    assert [sinal8(u) for u in (0, 127, 128, 252, 255)] == [0, 127, -128, -4, -1]
    assert codificar(LOAD, 1, 2, 12) == 0x360C
    assert codificar(LOAD, 1, 2, -4) == 0x36FC
    assert campos_ref(0x36FC)['imm16'] == 0xFFFC


def test_enderecador_referencia_e_fronteiras():
    montar_enderecador()
    sim = pyrtl.FastSimulation(tracer=None)
    rng = random.Random(7)
    casos = [dict(modo=m, base=b, indice=i, escala=e, imm8=d, direto=1012)
             for m in range(8) for b in (0, 2, 400, 65535)
             for i in (0, 7, 65535) for e in range(8) for d in (0, 127, 128, 252, 255)]
    casos += [dict(modo=rng.randrange(8), base=rng.randrange(65536),
                   indice=rng.randrange(65536), escala=rng.randrange(8),
                   imm8=rng.randrange(256), direto=rng.randrange(65536)) for _ in range(1000)]
    for entrada in casos:
        sim.step(entrada)
        esperado = endereco_ref(**entrada)
        assert {n: sim.inspect(n) for n in esperado} == esperado
    assert endereco_ref(INDEXADO, base=400, indice=7, escala=4)['ea'] == 428
    assert endereco_ref(4, base=2, imm8=252)['ea'] == 65534


@pytest.mark.parametrize('rd', range(4))
@pytest.mark.parametrize('imm,addr', [(12, 1012), (-4, 996)])
def test_carga_e_preservacao(rd, imm, addr):
    inicial = (10, 20, 1000, 40)
    t = simular_carga(codificar(LOAD, rd, 2, imm), inicial, {addr: 0x34, addr+1: 0x12})
    assert t[0]['ea'] == addr and t[0]['dado'] == 0x1234
    assert t[0]['reg_write'] == 1 and t[0][f'r{rd}'] == inicial[rd]
    assert t[1][f'r{rd}'] == 0x1234 and t[1]['reg_write'] == 0
    for i in range(4):
        if i != rd:
            assert t[1][f'r{i}'] == inicial[i]


def test_reset_e_enable():
    ins = codificar(LOAD, 1, 2, 12)
    t = simular_carga(ins, (8, 9, 1000, 7), {1012: 37}, habilita=(0, 0))
    assert t[1]['r1'] == 9 and t[0]['reg_write'] == 0
    t = simular_carga(ins, (8, 9, 1000, 7), {1012: 37}, reset=(1, 0))
    assert t[0]['reg_write'] == t[0]['erro'] == 0
    assert [t[1][f'r{i}'] for i in range(4)] == [0, 0, 0, 0]


@pytest.mark.parametrize('instr', [0, codificar(LOAD, 1, 2, 13), codificar(STORE, 1, 2, 12)])
def test_recorte_rejeita_nao_load_ou_desalinhado(instr):
    t = simular_carga(instr, (0, 9, 1000, 0))
    assert t[0]['erro'] == 1 and t[0]['reg_write'] == t[0]['mem_read'] == 0
    assert t[1]['r1'] == 9


def test_wrap_e_memoria_zero():
    t = simular_carga(codificar(LOAD, 1, 2, -4), (0, 0, 2, 0), {65534: 0x78, 65535: 0x56})
    assert t[0]['ea'] == 65534 and t[1]['r1'] == 0x5678
    t = simular_carga(codificar(LOAD, 1, 2, 12), (0, 9, 1000, 0))
    assert t[1]['r1'] == 0  # Política explícita de inicialização do modelo.
