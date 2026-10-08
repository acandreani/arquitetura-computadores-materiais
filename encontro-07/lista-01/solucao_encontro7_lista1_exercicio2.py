"""Encontro 7, Lista 1, exercício 2: 16 combinações de LOAD.

Instale: python -m pip install pyrtl==1.0.3
Execute: python encontro-07/lista-01/solucao_encontro7_lista1_exercicio2.py

Base de codificação/decodificação incorporada do laboratório do encontro 7
para que esta solução não dependa de arquivos ainda não publicados.
Não inclui execução de LOAD, RAM ou banco de registradores.

Formato: opcode[15:12], rd[11:10], base[9:8], imediato[7:0].
LOAD R1,[R2+12]: 0011 | 01 | 10 | 00001100 = 0x360C = 13836.
(3 << 12) | (1 << 10) | (2 << 8) | 12 posiciona e combina os campos.

Índice não é conteúdo: se R2=1000 e R3=2000, selecionar base=2 ou base=3
produziria endereços 1012 ou 2012 na execução. Isso não escreve 2 ou 3
nesses registradores. Trocar rd apenas seleciona outro destino futuro.
O decodificador somente extrai campos e sinais; escreve_reg=1 indica a
classe da instrução, não que uma escrita já aconteceu.
"""

import pyrtl

MOVI, MOV, LOAD, STORE, ADDI = 1, 2, 3, 4, 5


def faixa(nome, valor, minimo, maximo):
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ValueError(f'{nome}: esperado inteiro entre {minimo} e {maximo}')


def sinal8(u):
    faixa('u', u, 0, 255)
    return u - 256 if u & 128 else u


def campos_ref(instr):
    faixa('instr', instr, 0, 65535)
    op = (instr >> 12) & 15
    rd, base, imm = (instr >> 10) & 3, (instr >> 8) & 3, instr & 255
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


def montar_decodificador():
    pyrtl.reset_working_block()
    instr = pyrtl.Input(16, 'instr')
    for nome, fio in campos_hw(instr).items():
        saida = pyrtl.Output(len(fio), nome)
        saida <<= fio


def resolver():
    # 1. Constrói o circuito uma vez, antes de criar o simulador.
    montar_decodificador()
    sim = pyrtl.Simulation()
    assert codificar(LOAD, 1, 2, 12) == 0x360C == 13836
    palavras = set()

    # 2. Quatro destinos vezes quatro bases: 16 instruções.
    for rd in range(4):
        for base in range(4):
            palavra = codificar(LOAD, rd, base, 12)
            sim.step({'instr': palavra})
            esperado = dict(opcode=LOAD, rd=rd, base=base, imm8=12,
                            imm16=12, valido=1, is_load=1, is_store=0,
                            escreve_reg=1)
            observado = {nome: sim.inspect(nome) for nome in esperado}

            # 3. Confere todas as saídas, não apenas a palavra codificada.
            assert observado == esperado, (f'0x{palavra:04X}', observado)
            assert palavra not in palavras
            palavras.add(palavra)
            print(f'LOAD R{rd},[R{base}+12] -> 0x{palavra:04X} '
                  f'| {palavra:016b} | {observado}')

    assert len(palavras) == 16
    print('16 combinações aprovadas.')


if __name__ == '__main__':
    resolver()
