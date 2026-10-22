"""Assembly simbólico didático + somador de vetor em PyRTL, não uma CPU.

R0..R3: 32 bits, R0 comum. PC/RA: índices de instruções, não bytes.
RAM: bytes little-endian; LOAD/PUSH/POP de 32 bits, alinhados em 4.
Pilha descendente [768,1000), SP inicial 1000; CALL usa RA separado.
O interpretador rejeita leituras não inicializadas; o wrapper PyRTL inicializa
todos os bytes acessados. MemBlock, isoladamente, usa zero para os omitidos.
"""
import re
import pyrtl

MASK = 0xFFFFFFFF
IDLE, RUN, DONE, ERROR = range(4)
SCHEMA = {'MOVI': 'ri', 'MOV': 'rr', 'ADD': 'rrr', 'ADDI': 'rri',
          'LOAD': 'rri', 'JZ': 'rt', 'JMP': 't', 'CALL': 't',
          'RET': '', 'PUSH': 's', 'POP': 's', 'HALT': ''}


def inteiro(v, lo, hi):
    if type(v) is not int or not lo <= v <= hi:
        raise ValueError(f'Esperado inteiro em [{lo}, {hi}]: {v}')
    return v


def montar(texto):
    """Duas passagens; saída é lista de tuplas, NÃO código binário da ISA 7."""
    linhas, rotulos = [], {}
    for raw in texto.splitlines():
        linha = raw.split(';')[0].strip()
        if not linha:
            continue
        if ':' in linha:
            nome, linha = (x.strip() for x in linha.split(':', 1))
            if not re.fullmatch(r'[A-Za-z_]\w*', nome) or nome in rotulos:
                raise ValueError('Rotulo invalido ou duplicado: ' + nome)
            rotulos[nome] = len(linhas)
        if linha:
            linhas.append(linha)
    codigo = []
    for linha in linhas:
        op, *args = linha.replace(',', ' ').split()
        op = op.upper()
        if op not in SCHEMA or len(args) != len(SCHEMA[op]):
            raise ValueError('Instrucao ou aridade invalida: ' + linha)
        valores = []
        for tipo, token in zip(SCHEMA[op], args):
            if tipo == 't':
                if token not in rotulos or rotulos[token] >= len(linhas):
                    raise ValueError('Destino inexistente: ' + token)
                valor = rotulos[token]
            elif tipo == 'i':
                valor = inteiro(int(token, 0), -(1 << 31), MASK)
            elif tipo == 's' and token.upper() == 'RA':
                valor = 'RA'
            else:
                if not re.fullmatch(r'R[0-3]', token.upper()):
                    raise ValueError('Registrador invalido: ' + token)
                valor = int(token[1])
            valores.append(valor)
        codigo.append((op, *valores))
    if not codigo:
        raise ValueError('Programa vazio')
    return codigo, rotulos


def endereco32(a):
    inteiro(a, 0, 65532)
    if a % 4:
        raise ValueError('Endereco desalinhado')
    return a


def gravar32(mem, a, valor):
    endereco32(a)
    inteiro(valor, 0, MASK)
    for k in range(4):
        mem[a+k] = (valor >> (8*k)) & 255


def ler32(mem, a):
    endereco32(a)
    if any(a+k not in mem for k in range(4)):
        raise ValueError('Leitura de byte nao inicializado')
    return sum(inteiro(mem[a+k], 0, 255) << (8*k) for k in range(4))


def memoria_vetor(valores, base=200):
    endereco32(base)
    if base + 4*len(valores) > 65536:
        raise ValueError('Vetor fora da memoria')
    mem = {}
    for i, valor in enumerate(valores):
        inteiro(valor, -(1 << 31), MASK)
        gravar32(mem, base+4*i, valor & MASK)
    return mem


def executar(texto, regs=(0, 0, 0, 0), memoria=None, limite=1000):
    codigo, rotulos = montar(texto)
    if len(regs) != 4:
        raise ValueError('Forneca quatro registradores')
    r = [inteiro(v, 0, MASK) for v in regs]
    inteiro(limite, 1, 1000000)
    mem = dict(memoria or {})
    for a, v in mem.items():
        inteiro(a, 0, 65535); inteiro(v, 0, 255)
    pc, ra, sp, trace = 0, None, 1000, []
    for passo in range(limite):
        if not 0 <= pc < len(codigo):
            raise ValueError('PC fora do programa')
        op, *a = codigo[pc]
        antes = dict(pc=pc, ra=ra, sp=sp, regs=r.copy())
        prox = pc+1
        if op == 'MOVI': r[a[0]] = a[1] & MASK
        elif op == 'MOV': r[a[0]] = r[a[1]]
        elif op == 'ADD': r[a[0]] = (r[a[1]]+r[a[2]]) & MASK
        elif op == 'ADDI': r[a[0]] = (r[a[1]]+a[2]) & MASK
        elif op == 'LOAD': r[a[0]] = ler32(mem, r[a[1]]+a[2])
        elif op == 'JZ':
            if r[a[0]] == 0: prox = a[1]
        elif op == 'JMP': prox = a[0]
        elif op == 'CALL': ra, prox = pc+1, a[0]
        elif op == 'RET':
            if ra is None or not 0 <= ra < len(codigo):
                raise ValueError('RA sem retorno valido')
            prox = ra
        elif op == 'PUSH':
            valor = ra if a[0] == 'RA' else r[a[0]]
            if valor is None or sp-4 < 768:
                raise ValueError('Pilha cheia ou RA nao definido')
            sp -= 4; gravar32(mem, sp, valor)
        elif op == 'POP':
            if sp >= 1000: raise ValueError('Pilha vazia')
            valor = ler32(mem, sp); sp += 4
            if a[0] == 'RA': ra = valor
            else: r[a[0]] = valor
        elif op == 'HALT': prox = pc
        trace.append(dict(passo=passo, instrucao=codigo[pc], antes=antes,
                          depois=dict(pc=prox, ra=ra, sp=sp, regs=r.copy())))
        pc = prox
        if op == 'HALT':
            return dict(regs=r, sp=sp, ra=ra, memoria=mem, trace=trace, rotulos=rotulos)
    raise RuntimeError('Limite de instrucoes excedido; possivel laco infinito')


FOLHA = '''
CALL soma
HALT
soma: ADD R0,R0,R1
RET
'''

NAO_FOLHA = '''
CALL soma_mais_um
HALT
soma_mais_um: PUSH RA
PUSH R2
CALL soma
MOVI R2,1
ADD R0,R0,R2
POP R2
POP RA
RET
soma: ADD R0,R0,R1
RET
'''

VETOR = '''
MOVI R0,0
laco: JZ R1,fim
LOAD R3,R2,0
ADD R0,R0,R3
ADDI R2,R2,4
ADDI R1,R1,-1
JMP laco
fim: HALT
'''


def montar_somador():
    """FSM especializada: captura base/n; soma um elemento por ciclo habilitado.

    IDLE -> RUN -> DONE ou IDLE -> ERROR. DONE/ERROR persistem ate reset.
    Reset sincrono prioritario; habilita=0 pausa estado, i e acumulador.
    Solicitações start fora de IDLE são ignoradas. Não executa assembly.
    """
    pyrtl.reset_working_block()
    start, reset, hab = [pyrtl.Input(1, n) for n in ('start', 'reset', 'habilita')]
    b_in, n_in = pyrtl.Input(16, 'base_in'), pyrtl.Input(8, 'n_in')
    estado = pyrtl.Register(2, 'estado')
    base, n = pyrtl.Register(16, 'base'), pyrtl.Register(8, 'n')
    i, acc = pyrtl.Register(8, 'i'), pyrtl.Register(32, 'acumulador')
    ram = pyrtl.MemBlock(8, 16, 'ram_bytes', asynchronous=True, max_read_ports=4)
    ea = (base + i.zero_extended(16)*4)[:16]
    bytes_ = [ram[(ea+k)[:16]] for k in range(4)]
    dado = pyrtl.concat(*reversed(bytes_))
    valido = (b_in[:2] == 0) & ((b_in.zero_extended(18) + n_in.zero_extended(18)*4) <= 65536)
    iniciar = hab & start & (estado == IDLE)
    ler = hab & ~reset & (estado == RUN) & (i < n)
    terminar = hab & (estado == RUN) & (i == n)
    estado.next <<= pyrtl.select(reset, IDLE, pyrtl.select(iniciar,
        pyrtl.select(valido, RUN, ERROR), pyrtl.select(terminar, DONE, estado)))
    base.next <<= pyrtl.select(reset, 0, pyrtl.select(iniciar, b_in, base))
    n.next <<= pyrtl.select(reset, 0, pyrtl.select(iniciar, n_in, n))
    i.next <<= pyrtl.select(reset | iniciar, 0, pyrtl.select(ler, i+1, i))
    acc.next <<= pyrtl.select(reset | iniciar, 0, pyrtl.select(ler, (acc+dado)[:32], acc))
    for nome, fio in dict(ea=ea, dado=dado, mem_read=ler,
                          done=(estado == DONE), erro=(estado == ERROR)).items():
        out = pyrtl.Output(len(fio), nome); out <<= fio
    return ram


def simular_vetor(valores, base=200):
    inteiro(len(valores), 0, 255)
    mem = memoria_vetor(valores, base)
    ram = montar_somador()
    sim = pyrtl.Simulation(memory_value_map={ram: mem})
    trace = []
    for ciclo in range(len(valores)+3):
        sim.step(dict(start=int(ciclo == 0), reset=0, habilita=1,
                      base_in=base, n_in=len(valores)))
        trace.append(dict(ciclo=ciclo, **{k: sim.inspect(k) for k in
                     ('estado', 'i', 'acumulador', 'ea', 'dado', 'mem_read', 'done', 'erro')}))
    assert trace[-1]['done'] == 1
    return trace


if __name__ == '__main__':
    for nome, programa in [('folha', FOLHA), ('nao_folha', NAO_FOLHA)]:
        resultado = executar(programa, regs=(5, 7, 99, 0))
        print(nome, resultado['regs'], 'SP=', resultado['sp'])
    valores = [3, 5, 7, 9]
    print('assembly:', executar(VETOR, regs=(0, 4, 200, 0),
                                memoria=memoria_vetor(valores))['regs'])
    for linha in simular_vetor(valores): print(linha)
