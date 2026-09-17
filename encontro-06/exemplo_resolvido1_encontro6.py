"""Encontro 6, Texto 1, Exemplo resolvido 1: ADD com controle autonomo.

Arquivo independente: requer apenas PyRTL (python -m pip install pyrtl).
Execute: python exemplo_resolvido1_encontro6.py

Reproduz o controle cabeado do caderno; o teste solicita ADD R1,R2,R3.
Uma linha mostra o estado ANTES da captura que encerra aquele ciclo.
"""
import pyrtl

IDLE, DECODE, ADD, SUB, JZ, DONE, TRAP = range(7)
NOMES = ["IDLE", "DECODE", "ADD", "SUB", "JZ", "DONE", "TRAP", "INVALIDO"]


def construir():
    pyrtl.reset_working_block()

    # 1. Interface de solicitacao. O teste nao fornece os enables internos.
    start = pyrtl.Input(1, "start")
    reset = pyrtl.Input(1, "reset")
    opcode = pyrtl.Input(2, "opcode")

    # 2. Estado armazenado: etapa, instrucao e caminho de dados.
    estado = pyrtl.Register(3, "estado")
    ir = pyrtl.Register(2, "ir")
    r1 = pyrtl.Register(8, "r1")
    r2 = pyrtl.Register(8, "r2")
    r3 = pyrtl.Register(8, "r3")
    pc = pyrtl.Register(8, "pc")

    # 3. IR captura opcode apenas quando a solicitacao e aceita em IDLE.
    aceitar = (estado == IDLE) & start
    ir.next <<= pyrtl.select(reset, truecase=0, falsecase=
        pyrtl.select(aceitar, truecase=opcode, falsecase=ir))

    # 4. Decodificacao do IR armazenado: 0=ADD, 1=SUB, 2=JZ, 3=invalido.
    despacho = pyrtl.mux(ir, ADD, SUB, JZ, TRAP)
    proximo = pyrtl.mux(estado,
        pyrtl.select(start, truecase=DECODE, falsecase=IDLE),
        despacho, DONE, DONE, DONE, IDLE, TRAP, TRAP)
    estado.next <<= pyrtl.select(reset, truecase=IDLE, falsecase=proximo)

    # 5. Sinais produzidos pelo controle, nao pelo programa de teste.
    reg_write = ((estado == ADD) | (estado == SUB)) & ~reset
    alu_sub = estado == SUB
    zero = r1 == 0
    pc_write = (estado == JZ) & zero & ~reset
    done = (estado == DONE) & ~reset
    trap = ((estado == TRAP) | (estado == 7)) & ~reset

    # 6. A ULA e combinacional. So o enable permite capturar seu resultado.
    resultado = pyrtl.select(alu_sub, truecase=(r2 - r3)[:8],
                            falsecase=(r2 + r3)[:8])
    r1.next <<= pyrtl.select(reset, truecase=0, falsecase=
        pyrtl.select(reg_write, truecase=resultado, falsecase=r1))
    r2.next <<= r2  # operandos constantes neste recorte
    r3.next <<= r3
    pc.next <<= pyrtl.select(reset, truecase=0, falsecase=
        pyrtl.select(pc_write, truecase=0x40, falsecase=pc))

    for nome, sinal in [("reg_write", reg_write), ("alu_sub", alu_sub),
                        ("alu_out", resultado), ("done", done),
                        ("pc_write", pc_write), ("trap", trap)]:
        saida = pyrtl.Output(len(sinal), nome)
        saida <<= sinal
    return r2, r3


def executar(a=5, b=7, mostrar=True):
    r2, r3 = construir()
    trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=trace, register_value_map={r2: a, r3: b})
    linhas = []
    for ciclo in range(5):
        sim.step({"start": int(ciclo == 0), "reset": 0, "opcode": 0})
        nomes = ("estado", "ir", "reg_write", "alu_sub", "alu_out",
                 "r1", "r2", "r3", "pc", "pc_write", "done", "trap")
        linhas.append({nome: sim.inspect(nome) for nome in nomes})

    esperado = (a + b) & 0xFF
    assert [x["estado"] for x in linhas] == [IDLE, DECODE, ADD, DONE, IDLE]
    assert [x["reg_write"] for x in linhas] == [0, 0, 1, 0, 0]
    assert [x["r1"] for x in linhas] == [0, 0, 0, esperado, esperado]
    assert [x["done"] for x in linhas] == [0, 0, 0, 1, 0]
    for linha in linhas:
        assert linha["ir"] == linha["alu_sub"] == linha["trap"] == 0
        assert linha["pc"] == linha["pc_write"] == 0
        assert (linha["r2"], linha["r3"]) == (a, b)
        assert linha["alu_out"] == esperado

    if mostrar:
        print("ciclo estado  IR reg_write ULA R1 done")
        for ciclo, x in enumerate(linhas):
            print(f'{ciclo:5} {NOMES[x["estado"]]:7} {x["ir"]:2}'
                  f' {x["reg_write"]:9} {x["alu_out"]:3}'
                  f' {x["r1"]:2} {x["done"]:4}')
        print("\nEm ADD, R1 ainda mostra 0; em DONE, mostra", esperado)
        print("O valor em reg.next aparece no inicio do proximo step.\n")
        trace.render_trace(trace_list=["estado", "ir", "reg_write", "r1", "done"])
    return linhas


if __name__ == "__main__":
    executar()
    executar(a=250, b=10, mostrar=False)
    print("\nTestes passaram: 5+7=12 e (250+10) mod 256=4.")
