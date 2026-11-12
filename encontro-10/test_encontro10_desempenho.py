import random
import pytest
from encontro10_desempenho import resumo, amdahl, medir, monitorar


def test_resumo():
    assert resumo([10,11,9,10,30]) == dict(n=5,media=14,mediana=10,minimo=9,maximo=30)


@pytest.mark.parametrize('a', [[], [0], [-1], [float('nan')], [float('inf')], [True]])
def test_resumo_invalido(a):
    with pytest.raises(ValueError): resumo(a)


@pytest.mark.parametrize('p,s,rel', [(0,4,1),(1,4,.25),(.8,4,.4),(.7,5,.44),(.5,1,1)])
def test_amdahl(p,s,rel):
    r=amdahl(p,s)
    assert r['relativo'] == pytest.approx(rel)
    assert r['speedup'] == pytest.approx(1/rel)


def test_overhead_e_novo_perfil():
    assert amdahl(.8,4)['fracao_restante'] == pytest.approx(.5)
    assert amdahl(.8,4,.1)['speedup'] == pytest.approx(2)


@pytest.mark.parametrize('args', [(-.1,2),(1.1,2),(.5,0),(.5,-1),(.5,2,-1),(.5,float('inf'))])
def test_amdahl_invalido(args):
    with pytest.raises(ValueError): amdahl(*args)


def test_medir():
    amostras=medir(lambda:42,42,repeticoes=3,lote=10)
    assert len(amostras)==3 and all(x>=0 for x in amostras)
    with pytest.raises(ValueError): medir(lambda:41,42)
    with pytest.raises(ValueError): medir(lambda:42,42,lote=0)


def test_trace():
    eventos=[dict(reset=0,enable=1,retire=r,stall=1-r) for r in (1,0,1,0,1,1)]
    t=monitorar(eventos)
    assert t[0]==dict(ciclos=0,concluidas=0,esperas=0)
    assert t[-1]==dict(ciclos=6,concluidas=4,esperas=2)


@pytest.mark.parametrize('bits',[1,2,4,16])
def test_diferencial(bits):
    rng=random.Random(10)
    eventos=[dict(reset=int(rng.random()<.1),enable=rng.randrange(2),
                  retire=rng.randrange(2),stall=rng.randrange(2)) for _ in range(300)]
    ref=dict(ciclos=0,concluidas=0,esperas=0)
    trace=monitorar(eventos,bits)
    for i,e in enumerate(eventos):
        assert trace[i]==ref
        if e['reset']: ref=dict(ciclos=0,concluidas=0,esperas=0)
        elif e['enable']:
            ref={k:(v+inc)%(1<<bits) for (k,v),inc in zip(ref.items(),(1,e['retire'],e['stall']))}
    assert trace[-1]==ref


def test_pausa_reset_wrap():
    def e(reset=0,enable=1): return dict(reset=reset,enable=enable,retire=1,stall=1)
    assert monitorar([e()]*4,bits=2)[-1]==dict(ciclos=0,concluidas=0,esperas=0)
    assert monitorar([e(),e(enable=0)])[-1]['ciclos']==1
    assert monitorar([e(),e(reset=1,enable=0)])[-1]['ciclos']==0


@pytest.mark.parametrize('e',[{},dict(reset=0,enable=2,retire=0,stall=0)])
def test_eventos_invalidos(e):
    with pytest.raises(ValueError): monitorar([e])
