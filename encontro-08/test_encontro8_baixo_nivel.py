import random
import pytest
import pyrtl
from encontro8_baixo_nivel import (
    montar, executar, memoria_vetor, ler32, gravar32, simular_vetor,
    montar_somador, FOLHA, NAO_FOLHA, VETOR, MASK, IDLE, RUN, DONE, ERROR,
)


def test_rotulos():
    codigo, nomes = montar('; comentario\nCALL fim\nHALT\nfim: RET')
    assert nomes == {'fim': 2}
    assert codigo == [('CALL', 2), ('HALT',), ('RET',)]


@pytest.mark.parametrize('texto', ['x: HALT\nx: RET', 'JMP falta', 'ADD R0,R1',
                                  'MOVI R4,2', 'BOGUS', 'HALT 1', '',
                                  'JMP fim\nfim:', 'MOVI R0,4294967296'])
def test_montagem_invalida(texto):
    with pytest.raises(ValueError): montar(texto)


def test_folha():
    r = executar(FOLHA, (5, 7, 99, 123))
    assert r['regs'] == [12, 7, 99, 123] and r['sp'] == 1000


def test_nao_folha():
    r = executar(NAO_FOLHA, (5, 7, 99, 123))
    assert r['regs'] == [13, 7, 99, 123] and r['sp'] == 1000
    assert min(t['depois']['sp'] for t in r['trace']) == 992
    assert ler32(r['memoria'], 996) == 1
    assert ler32(r['memoria'], 992) == 99


def test_ra_nao_preservado():
    ruim = NAO_FOLHA.replace('PUSH RA', '').replace('POP RA', '')
    with pytest.raises(ValueError, match='vazia'): executar(ruim, (5, 7, 99, 0))


@pytest.mark.parametrize('texto', ['POP R0\nHALT', 'RET', 'l: PUSH R0\nJMP l'])
def test_pilha_e_retorno_invalidos(texto):
    with pytest.raises(ValueError): executar(texto)


def test_limite_laco():
    with pytest.raises(RuntimeError): executar('l: JMP l', limite=10)


def test_little_endian():
    mem = {}; gravar32(mem, 200, 0x12345678)
    assert list(mem.values()) == [0x78, 0x56, 0x34, 0x12]
    assert ler32(mem, 200) == 0x12345678


@pytest.mark.parametrize('a', [201, -4, 65536])
def test_endereco_invalido(a):
    with pytest.raises(ValueError): ler32({}, a)


def test_memoria_ausente():
    with pytest.raises(ValueError, match='inicializado'): ler32({200: 3}, 200)


@pytest.mark.parametrize('valores', [[], [9], [3,5,7,9], [-1,2], [MASK,1], [0]*255])
def test_equivalencia(valores):
    ref = sum(valores) & MASK
    r = executar(VETOR, (0,len(valores),200,0), memoria_vetor(valores), limite=2000)
    hw = simular_vetor(valores)
    assert r['regs'][0] == hw[-1]['acumulador'] == ref
    assert r['regs'][1] == 0 and r['regs'][2] == 200+4*len(valores)
    assert [t['ea'] for t in hw if t['mem_read']] == list(range(200,200+4*len(valores),4))
    assert sum(t['mem_read'] for t in hw) == len(valores)


def test_trace_quatro():
    t = simular_vetor([3,5,7,9])
    assert [x['acumulador'] for x in t] == [0,0,3,8,15,24,24]
    assert [x['estado'] for x in t] == [IDLE,RUN,RUN,RUN,RUN,RUN,DONE]
    assert [x['mem_read'] for x in t] == [0,1,1,1,1,0,0]


def test_equivalencia_aleatoria():
    rng = random.Random(8)
    for _ in range(40):
        v = [rng.randrange(-(1<<31),1<<31) for _ in range(rng.randrange(12))]
        assert simular_vetor(v)[-1]['acumulador'] == sum(v) & MASK


def test_ultima_palavra():
    t = simular_vetor([7], base=65532)
    assert t[-1]['acumulador'] == 7
    assert [x['ea'] for x in t if x['mem_read']] == [65532]


@pytest.mark.parametrize('base,n', [(201,4),(65532,2),(1,0)])
def test_hw_rejeita(base,n):
    montar_somador(); sim = pyrtl.Simulation()
    for start in (1,0,0):
        sim.step(dict(start=start,reset=0,habilita=1,base_in=base,n_in=n))
    assert sim.inspect('estado') == ERROR and sim.inspect('mem_read') == 0


def test_pausa_reset_e_start():
    ram = montar_somador(); sim = pyrtl.Simulation(memory_value_map={ram:memoria_vetor([3,5])})
    def step(start=0, reset=0, habilita=1, base_in=200, n_in=2):
        sim.step(dict(start=start,reset=reset,habilita=habilita,base_in=base_in,n_in=n_in))
        return tuple(sim.inspect(k) for k in ('estado','i','acumulador','mem_read'))
    assert step(start=1) == (IDLE,0,0,0)
    assert step(habilita=0) == (RUN,0,0,0)
    assert step(habilita=0) == (RUN,0,0,0)
    assert step(start=1,base_in=400,n_in=7) == (RUN,0,0,1)
    assert step() == (RUN,1,3,1)
    assert step() == (RUN,2,8,0)
    assert step(start=1) == (DONE,2,8,0)
    assert step(reset=1,habilita=0) == (DONE,2,8,0)
    assert step() == (IDLE,0,0,0)


def test_erro_de_escala():
    ruim = VETOR.replace('ADDI R2,R2,4','ADDI R2,R2,1')
    with pytest.raises(ValueError, match='desalinhado'):
        executar(ruim,(0,4,200,0),memoria_vetor([3,5,7,9]))
