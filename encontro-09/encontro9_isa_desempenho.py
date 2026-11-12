"""Modelos didáticos: custo agregado e decoder de 16 bits, não ARM/x86/MIPS.

PyRTL modela apenas lógica combinacional. Não mede GHz, CPI ou energia reais.
Formato: opcode[15:12], rd[11:10], rs[9:8], campo[7:0].
ADD=1 exige campo zero; LOAD=2 e ADDM=3 aceitam offset com sinal de 8 bits.
ADDM significa rd <- rd + M[rs+offset]; nenhum acesso é executado aqui.
"""
import math
import pyrtl

ADD, LOAD, ADDM = 1, 2, 3


def positivo(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError('Esperado numero real positivo e finito')
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError('Esperado numero real positivo e finito')
    return valor


def metricas(ic, cpi, ghz, watts):
    """Custo hipotético para o MESMO trabalho; potência média em watts."""
    for v in (ic, cpi, ghz, watts):
        positivo(v)
    ciclos = ic * cpi
    segundos = ciclos / (ghz * 1e9)
    return dict(ciclos=ciclos, segundos=segundos, joules=watts*segundos)


def cpi_medio(classes):
    """Pares (contagem dinâmica inteira, CPI da classe); não média simples."""
    classes = list(classes)
    if not classes:
        raise ValueError('Mistura vazia')
    for n, cpi in classes:
        if type(n) is not int or n < 0:
            raise ValueError('Contagem deve ser inteiro nao negativo')
        positivo(cpi)
    total = sum(n for n, _ in classes)
    if not total:
        raise ValueError('Total deve ser positivo')
    return sum(n*cpi for n, cpi in classes)/total


def inteiro(v, lo, hi):
    if type(v) is not int or not lo <= v <= hi:
        raise ValueError(f'Esperado inteiro entre {lo} e {hi}')
    return v


def decodificar_ref(palavra):
    inteiro(palavra, 0, 65535)
    op, rd, rs, campo = palavra >> 12, (palavra >> 10) & 3, (palavra >> 8) & 3, palavra & 255
    valido = op in (ADD, LOAD, ADDM) and (op != ADD or campo == 0)
    return dict(opcode=op, rd=rd, rs=rs, offset16=(campo if campo < 128 else campo-256) & 65535,
                valido=int(valido), mem_read=int(valido and op in (LOAD, ADDM)),
                alu_add=int(valido and op in (ADD, ADDM)), reg_write=int(valido))


def codificar(op, rd, rs, offset=0):
    inteiro(op, 0, 15); inteiro(rd, 0, 3); inteiro(rs, 0, 3); inteiro(offset, -128, 127)
    palavra = (op << 12) | (rd << 10) | (rs << 8) | (offset & 255)
    if not decodificar_ref(palavra)['valido']:
        raise ValueError('Opcode ou campo reservado invalido')
    return palavra


def montar_decoder():
    """Reinicializa o bloco: construa uma nova Simulation depois desta chamada."""
    pyrtl.reset_working_block()
    palavra = pyrtl.Input(16, 'instr')
    op, rd, rs, campo = palavra[12:16], palavra[10:12], palavra[8:10], palavra[:8]
    valido = ((op == ADD) | (op == LOAD) | (op == ADDM)) & ((op != ADD) | (campo == 0))
    sinais = dict(opcode=op, rd=rd, rs=rs, offset16=campo.sign_extended(16),
                  valido=valido, mem_read=valido & ((op == LOAD) | (op == ADDM)),
                  alu_add=valido & ((op == ADD) | (op == ADDM)), reg_write=valido)
    for nome, fio in sinais.items():
        saida = pyrtl.Output(len(fio), nome)
        saida <<= fio


def expandir(palavra):
    """Sequência conceitual, não micro-ops reais nem contagem de clocks.

    T é um temporário invisível à ISA. Nenhuma memória ou ULA é simulada.
    """
    d = decodificar_ref(palavra)
    if not d['valido']:
        raise ValueError('Instrucao invalida')
    return {ADD: ('SOMAR_REGS', 'ESCREVER_RD'),
            LOAD: ('CALCULAR_EA', 'LER_T', 'ESCREVER_RD'),
            ADDM: ('CALCULAR_EA', 'LER_T', 'SOMAR_RD_T', 'ESCREVER_RD')}[d['opcode']]


def exemplos():
    for nome, dados in [('A', (1e6, 1.5, 2, 10)), ('B', (1.2e6, 1.05, 2, 8))]:
        print(nome, metricas(*dados))
    print('CPI ponderado:', cpi_medio([(600, 1), (300, 3), (100, 2)]))
    montar_decoder()
    sim = pyrtl.Simulation()
    for op in (ADD, LOAD, ADDM):
        palavra = codificar(op, 1, 2, 0 if op == ADD else -4)
        sim.step({'instr': palavra})
        print(hex(palavra), {n: sim.inspect(n) for n in decodificar_ref(palavra)}, expandir(palavra))


if __name__ == '__main__':
    exemplos()
