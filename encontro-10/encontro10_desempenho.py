"""Medições, Amdahl e monitor PyRTL didático; não mede frequência física."""
import math
import statistics
from time import perf_counter_ns
import pyrtl


def real(v, minimo=0, aberto=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError('Numero finito esperado')
    if v < minimo or (aberto and v == minimo):
        raise ValueError('Valor fora da faixa')
    return v


def resumo(amostras):
    valores = list(amostras)
    if not valores:
        raise ValueError('Amostra vazia')
    for v in valores: real(v, aberto=True)
    return dict(n=len(valores), media=statistics.mean(valores),
                mediana=statistics.median(valores), minimo=min(valores), maximo=max(valores))


def amdahl(p, s, overhead=0):
    real(p); real(s, aberto=True); real(overhead)
    if p > 1: raise ValueError('Fracao maior que um')
    relativo = 1-p+p/s+overhead
    return dict(relativo=relativo, speedup=1/relativo,
                fracao_restante=(1-p)/relativo)


def medir(funcao, esperado, repeticoes=7, lote=100, aquecimentos=2):
    """Tempo de parede por chamada em ns; função sem efeitos persistentes.

    Inclui chamada Python e controle do laço; exclui impressão e validação.
    Retorna amostras brutas. Não é benchmark de uma ISA.
    """
    for n, minimo in ((repeticoes, 1), (lote, 1), (aquecimentos, 0)):
        if type(n) is not int or n < minimo: raise ValueError('Contagem invalida')
    for _ in range(aquecimentos+1):
        if funcao() != esperado: raise ValueError('Resultado incorreto')
    amostras = []
    for _ in range(repeticoes):
        inicio = perf_counter_ns()
        for _ in range(lote): resultado = funcao()
        fim = perf_counter_ns()
        if resultado != esperado: raise ValueError('Resultado incorreto')
        amostras.append((fim-inicio)/lote)
    return amostras


def montar_monitor(bits=16):
    """Conta eventos por ciclo habilitado, no máximo um retire por ciclo.

    Reset síncrono prioritário; sem enable preserva estado. Contadores modulares.
    retire=1 denota operação concluída; stall pode coexistir com retire.
    """
    if type(bits) is not int or not 1 <= bits <= 64: raise ValueError('Largura invalida')
    pyrtl.reset_working_block()
    rst, en, ret, stall = [pyrtl.Input(1,n) for n in ('reset','enable','retire','stall')]
    eventos = dict(ciclos=en, concluidas=en & ret, esperas=en & stall)
    for nome, evento in eventos.items():
        r = pyrtl.Register(bits, nome)
        r.next <<= pyrtl.select(rst, 0, r+evento)


def monitorar(eventos, bits=16):
    eventos = list(eventos)
    for e in eventos:
        if set(e) != {'reset','enable','retire','stall'}:
            raise ValueError('Campos invalidos')
        if any(type(v) is not int or v not in (0,1) for v in e.values()):
            raise ValueError('Sinais devem ser bits inteiros')
    montar_monitor(bits)
    sim = pyrtl.Simulation()
    trace = []
    # Última observação desabilitada revela a atualização do último evento.
    for e in eventos + [dict(reset=0, enable=0, retire=0, stall=0)]:
        sim.step(e)
        trace.append({n:sim.inspect(n) for n in ('ciclos','concluidas','esperas')})
    return trace


if __name__ == '__main__':
    print('Amostras em ms:', resumo([10,11,9,10,30]))
    print('Amdahl:', amdahl(.8,4))
    eventos = [dict(reset=0,enable=1,retire=r,stall=1-r) for r in (1,0,1,0,1,1)]
    print('Monitor:', monitorar(eventos))
    dados = tuple(range(1000))
    amostras = medir(lambda: sum(dados), 499500)
    print('Tempos brutos ns/chamada:', amostras)
    print('Resumo ns/chamada:', resumo(amostras))
