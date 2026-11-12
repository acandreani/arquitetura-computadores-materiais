import math
import pytest
import pyrtl
from encontro9_isa_desempenho import (
    metricas, cpi_medio, codificar, decodificar_ref, montar_decoder, expandir,
    ADD, LOAD, ADDM,
)


def test_exemplo_tempo():
    a, b = metricas(1e6, 1.5, 2, 10), metricas(1.2e6, 1.05, 2, 8)
    assert a['segundos'] == pytest.approx(.00075)
    assert b['segundos'] == pytest.approx(.00063)
    assert b['segundos']/a['segundos'] == pytest.approx(.84)
    assert a['joules'] == pytest.approx(.0075)
    assert b['joules'] == pytest.approx(.00504)


@pytest.mark.parametrize('v', [0, -1, math.inf, math.nan, True, '2'])
def test_metricas_rejeitam(v):
    for i in range(4):
        args = [100, 1, 2, 3]; args[i] = v
        with pytest.raises(ValueError): metricas(*args)


def test_mistura():
    assert cpi_medio([(600, 1), (300, 3), (100, 2)]) == pytest.approx(1.7)
    assert cpi_medio([(0, 5), (10, 2)]) == 2


@pytest.mark.parametrize('mistura', [[], [(0, 1)], [(-1, 2)], [(1.5, 2)], [(True, 2)], [(1, 0)]])
def test_mistura_invalida(mistura):
    with pytest.raises(ValueError): cpi_medio(mistura)


def test_decoder_exaustivo():
    montar_decoder(); sim = pyrtl.FastSimulation(tracer=None)
    validas = 0
    for palavra in range(65536):
        ref = decodificar_ref(palavra)
        sim.step({'instr': palavra})
        assert {n: sim.inspect(n) for n in ref} == ref
        validas += ref['valido']
        if not ref['valido']:
            assert ref['mem_read'] == ref['alu_add'] == ref['reg_write'] == 0
    assert validas == 16 + 2*4096


@pytest.mark.parametrize('op', [ADD, LOAD, ADDM])
def test_roundtrip(op):
    for rd in range(4):
        for rs in range(4):
            for off in ([0] if op == ADD else [-128, -4, 0, 127]):
                d = decodificar_ref(codificar(op, rd, rs, off))
                assert (d['opcode'], d['rd'], d['rs'], d['offset16']) == (op, rd, rs, off & 65535)


@pytest.mark.parametrize('args', [(0,0,0,0), (ADD,1,2,1), (LOAD,4,0,0),
                                 (LOAD,0,-1,0), (LOAD,0,0,128), (LOAD,0,0,-129)])
def test_encoder_invalido(args):
    with pytest.raises(ValueError): codificar(*args)


def test_exemplo_decoder():
    assert codificar(ADDM,1,2,-4) == 0x36FC
    assert expandir(0x36FC) == ('CALCULAR_EA','LER_T','SOMAR_RD_T','ESCREVER_RD')
    with pytest.raises(ValueError): expandir(0)


def test_clock_e_energia():
    a, b = metricas(1e8,1,2,5), metricas(1e8,1,4,12)
    assert a['segundos'] == 2*b['segundos']
    assert b['joules'] > a['joules']
