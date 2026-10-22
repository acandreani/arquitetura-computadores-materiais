"""ISA didática de 16 bits: campos, endereços e recorte de LOAD16.

Não é RISC-V, MVD-32 nem uma CPU completa. R0 é um registrador comum.
PyRTL constrói circuitos; as funções *_ref operam sobre inteiros Python.
RAM: bytes, little-endian, posições não inicializadas valem zero no simulador.
LOAD lê 16 bits alinhados; endereços usam aritmética modular de 16 bits.
"""
import pyrtl

MOVI, MOV, LOAD, STORE, ADDI = 1, 2, 3, 4, 5
IMEDIATO, REGISTRADOR, DIRETO, INDIRETO, BASE_OFFSET, INDEXADO = range(6)


def faixa(nome, valor, minimo, maximo):
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ValueError(f'{nome}: esperado inteiro entre {minimo} e {maximo}')


def sinal8(u):
    faixa('u', u, 0, 255)
    return u - 256 if u & 128 else u


def campos_ref(instr):
    faixa('instr', instr, 0, 65535)
    op, rd, base, imm = (instr >> 12) & 15, (instr >> 10) & 3, (instr >> 8) & 3, instr & 255
    valido = op in (MOVI, MOV, LOAD, STORE, ADDI)
    valido &= not (op == MOVI and base != 0)
    valido &= not (op == MOV and imm != 0)
    return dict(opcode=op, rd=rd, base=base, imm8=imm,
                imm16=sinal8(imm) & 65535, valido=int(valido),
                is_load=int(valido and op == LOAD),
                is_store=int(valido and op == STORE),
                escreve_reg=int(valido and op in (MOVI, MOV, LOAD, ADDI)))


def codificar(opcode, rd, base, imediato):
    for nome, valor, limite in [('opcode', opcode, 15), ('rd', rd, 3), ('base', base, 3)]:
        faixa(nome, valor, 0, limite)
    faixa('imediato', imediato, -128, 127)
    instr = (opcode << 12) | (rd << 10) | (base << 8) | (imediato & 255)
    if not campos_ref(instr)['valido']:
        raise ValueError('Opcode reservado ou campo sem uso diferente de zero')
    return instr


def campos_hw(instr):
    op, rd, base, imm = instr[12:16], instr[10:12], instr[8:10], instr[:8]
    conhecido = (op == MOVI) | (op == MOV) | (op == LOAD) | (op == STORE) | (op == ADDI)
    canonico = ((op != MOVI) | (base == 0)) & ((op != MOV) | (imm == 0))
    valido = conhecido & canonico
    return dict(opcode=op, rd=rd, base=base, imm8=imm, imm16=imm.sign_extended(16),
                valido=valido, is_load=valido & (op == LOAD),
                is_store=valido & (op == STORE),
                escreve_reg=valido & ((op == MOVI) | (op == MOV) | (op == LOAD) | (op == ADDI)))


def saidas(sinais):
    for nome, fio in sinais.items():
        o = pyrtl.Output(len(fio), nome)
        o <<= fio


def montar_decodificador():
    pyrtl.reset_working_block()
    instr = pyrtl.Input(16, 'instr')
    saidas(campos_hw(instr))


def endereco_ref(modo, base=0, indice=0, escala=1, imm8=0, direto=0):
    for nome, valor, limite in [('modo', modo, 7), ('base', base, 65535),
                                ('indice', indice, 65535), ('escala', escala, 7),
                                ('imm8', imm8, 255), ('direto', direto, 65535)]:
        faixa(nome, valor, 0, limite)
    valido = modo < 6 and (modo != INDEXADO or escala in (1, 2, 4))
    mem_read = valido and modo >= DIRETO
    candidatos = [0, 0, direto, base, base + sinal8(imm8),
                  base + indice * escala + sinal8(imm8), 0, 0]
    ea = candidatos[modo] & 65535 if mem_read else 0
    valor = (sinal8(imm8) & 65535) if valido and modo == IMEDIATO else base if valido and modo == REGISTRADOR else 0
    return dict(ea=ea, valor=valor, mem_read=int(mem_read), valido=int(valido))


def montar_enderecador():
    """Comparador de modos independente: modo/índice/escala NÃO vêm da ISA de 16 bits."""
    pyrtl.reset_working_block()
    modo = pyrtl.Input(3, 'modo')
    base, indice, direto = [pyrtl.Input(16, n) for n in ('base', 'indice', 'direto')]
    escala, imm = pyrtl.Input(3, 'escala'), pyrtl.Input(8, 'imm8')
    disp = imm.sign_extended(16)
    valido = (modo < 6) & ((modo != INDEXADO) | (escala == 1) | (escala == 2) | (escala == 4))
    leitura = valido & (modo >= DIRETO)
    candidato = pyrtl.mux(modo, pyrtl.Const(0, 16), pyrtl.Const(0, 16), direto,
                         base, (base + disp)[:16],
                         (base + indice * escala + disp)[:16],
                         pyrtl.Const(0, 16), pyrtl.Const(0, 16))
    valor = pyrtl.select(modo == IMEDIATO, disp,
                        pyrtl.select(modo == REGISTRADOR, base, pyrtl.Const(0, 16)))
    saidas(dict(ea=pyrtl.select(leitura, candidato, pyrtl.Const(0, 16)),
                valor=valor, mem_read=leitura, valido=valido))


def montar_carga():
    """Recorte combinacional + banco de registradores, sem busca, IR, PC ou FSM.

    habilita solicita uma carga na borda. reset síncrono tem prioridade.
    Sinais observados pertencem ao ciclo atual; reg.next aparece no próximo step.
    """
    pyrtl.reset_working_block()
    instr = pyrtl.Input(16, 'instr')
    habilita, reset = pyrtl.Input(1, 'habilita'), pyrtl.Input(1, 'reset')
    f = campos_hw(instr)
    regs = [pyrtl.Register(16, f'r{i}') for i in range(4)]
    base_valor = pyrtl.mux(f['base'], *regs)
    ea = (base_valor + f['imm16'])[:16]
    alinhado = ~ea[0]
    aceita = f['is_load'] & alinhado
    escrita = habilita & ~reset & aceita
    erro = habilita & ~reset & ~aceita
    ram = pyrtl.MemBlock(8, 16, 'ram_bytes', asynchronous=True, max_read_ports=2)
    baixo, alto = ram[ea], ram[(ea + 1)[:16]]
    dado = pyrtl.concat(alto, baixo)
    for i, r in enumerate(regs):
        r.next <<= pyrtl.select(reset, pyrtl.Const(0, 16),
                               pyrtl.select(escrita & (f['rd'] == i), dado, r))
    saidas(dict(ea=ea, dado=dado, reg_write=escrita, mem_read=escrita,
                erro=erro, alinhado=alinhado))
    return regs, ram


def simular_carga(instr, registradores=(0, 0, 1000, 0), memoria=None,
                  habilita=(1, 0), reset=None):
    faixa('instr', instr, 0, 65535)
    if len(registradores) != 4:
        raise ValueError('Forneca quatro registradores')
    for r in registradores:
        faixa('registrador', r, 0, 65535)
    memoria = {} if memoria is None else dict(memoria)
    for a, v in memoria.items():
        faixa('endereco', a, 0, 65535)
        faixa('byte', v, 0, 255)
    reset = [0] * len(habilita) if reset is None else reset
    if len(reset) != len(habilita):
        raise ValueError('Sequencias de controle com comprimentos diferentes')
    regs, ram = montar_carga()
    sim = pyrtl.Simulation(register_value_map=dict(zip(regs, registradores)),
                           memory_value_map={ram: memoria})
    nomes = ['ea', 'dado', 'reg_write', 'mem_read', 'erro', 'alinhado', 'r0', 'r1', 'r2', 'r3']
    linhas = []
    for ciclo, (h, rst) in enumerate(zip(habilita, reset)):
        faixa('habilita', h, 0, 1)
        faixa('reset', rst, 0, 1)
        sim.step(dict(instr=instr, habilita=h, reset=rst))
        linhas.append(dict(ciclo=ciclo, **{n: sim.inspect(n) for n in nomes}))
    return linhas


def exemplos():
    palavra = codificar(LOAD, 1, 2, 12)
    print(f'LOAD R1,[R2+12]: 0x{palavra:04X} = {palavra}')
    montar_decodificador()
    sim = pyrtl.Simulation()
    for imm in (12, -4):
        sim.step({'instr': codificar(LOAD, 1, 2, imm)})
        print('campos:', {n: sim.inspect(n) for n in campos_ref(palavra)})
    for linha in simular_carga(palavra, memoria={1012: 37, 1013: 0}):
        print('carga:', linha)
    montar_enderecador()
    sim = pyrtl.Simulation()
    sim.step(dict(modo=INDEXADO, base=400, indice=7, escala=4, imm8=0, direto=0))
    assert sim.inspect('ea') == 428
    print('Vetor: EA =', sim.inspect('ea'), '(nao e o dado)')


if __name__ == '__main__':
    exemplos()
