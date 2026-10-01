"""Exemplo 1, parte 2, encontro 6: ROM de ADD/SUB e diagrama transitions.

Instalacao: python -m pip install pyrtl transitions graphviz
O executavel Graphviz 'dot' tambem deve estar instalado no sistema.
Execucao: python exemplo1_parte2_encontro6.py
Saidas: tabela da ROM, traces, testes e diagramas PNG/SVG junto ao script.

PyRTL implementa o hardware; transitions modela e desenha o sequenciamento.
Referencia da API grafica: https://github.com/pytransitions/transitions
"""
from itertools import product
from pathlib import Path

import pyrtl
from transitions.extensions import GraphMachine

IDLE, DECODE, ADD, SUB, JZ, DONE, TRAP, INVALIDO = range(8)
NOMES = ["IDLE", "DECODE", "ADD", "SUB", "JZ", "DONE", "TRAP", "INVALIDO"]


def palavra(alvo, modo=0, rw=0, sub=0, pc_req=0, done=0, trap=0):
    """[9:7] alvo | [6:5] modo | trap done pc_req sub rw."""
    for valor, limite in [(alvo, 7), (modo, 3), (rw, 1), (sub, 1),
                           (pc_req, 1), (done, 1), (trap, 1)]:
        if not isinstance(valor, int) or not 0 <= valor <= limite:
            raise ValueError("campo fora da largura especificada")
    return ((alvo << 7) | (modo << 5) | (trap << 4)
            | (done << 3) | (pc_req << 2) | (sub << 1) | rw)


ROM = [palavra(DECODE, modo=1), palavra(0, modo=2),
       palavra(DONE, rw=1), palavra(DONE, rw=1, sub=1),
       palavra(DONE, pc_req=1), palavra(IDLE, done=1),
       palavra(TRAP, trap=1), palavra(TRAP, trap=1)]


def construir_hardware():
    pyrtl.reset_working_block()
    start, reset = pyrtl.Input(1, "start"), pyrtl.Input(1, "reset")
    opcode = pyrtl.Input(2, "opcode")
    upc = pyrtl.Register(3, "upc")
    ir = pyrtl.Register(2, "ir")
    r1, r2, r3 = [pyrtl.Register(8, nome) for nome in ("r1", "r2", "r3")]
    pc = pyrtl.Register(8, "pc")

    # 1. O microcontador endereca a memoria de controle (8 x 10 bits).
    memoria = pyrtl.RomBlock(10, 3, ROM, name="rom_controle")
    micro = memoria[upc]
    rw, sub, pc_req, fim, erro = [micro[i] for i in range(5)]
    modo, alvo = micro[5:7], micro[7:10]

    # 2. Sequenciador: direto, espera, despacho ou falha (modo reservado).
    despacho = pyrtl.mux(ir, ADD, SUB, JZ, TRAP)
    prox = pyrtl.mux(modo, alvo,
        pyrtl.select(start, truecase=alvo, falsecase=IDLE), despacho, TRAP)
    upc.next <<= pyrtl.select(reset, truecase=IDLE, falsecase=prox)
    aceitar = (upc == IDLE) & start
    ir.next <<= pyrtl.select(reset, 0, pyrtl.select(aceitar, opcode, ir))

    # 3. Caminho de dados. Resultado limitado a oito bits.
    we = rw & ~reset
    pc_we = pc_req & (r1 == 0) & ~reset
    resultado = pyrtl.select(sub, (r2 - r3)[:8], (r2 + r3)[:8])
    r1.next <<= pyrtl.select(reset, 0, pyrtl.select(we, resultado, r1))
    r2.next <<= r2
    r3.next <<= r3
    pc.next <<= pyrtl.select(reset, 0, pyrtl.select(pc_we, 0x40, pc))
    for nome, sinal in [("micro", micro), ("reg_write", we),
                        ("alu_sub", sub), ("alu_out", resultado),
                        ("pc_write", pc_we), ("done", fim & ~reset),
                        ("trap", erro & ~reset)]:
        saida = pyrtl.Output(len(sinal), nome)
        saida <<= sinal
    return {r.name: r for r in (upc, ir, r1, r2, r3, pc)}


def construir_maquina(inicial="IDLE"):
    """Eventos representam condicoes amostradas em uma borda, nao instrucoes."""
    transicoes = [
        ["start_0", "IDLE", "IDLE"],
        ["start_1", "IDLE", "DECODE"],
        ["ir_0", "DECODE", "ADD"], ["ir_1", "DECODE", "SUB"],
        ["ir_2", "DECODE", "JZ"], ["ir_3", "DECODE", "TRAP"],
        ["borda", "ADD", "DONE"], ["borda", "SUB", "DONE"],
        ["borda", "JZ", "DONE"], ["borda", "DONE", "IDLE"],
        ["borda", "TRAP", "TRAP"], ["borda", "INVALIDO", "TRAP"],
        ["reset_1", "*", "IDLE"],
    ]
    return GraphMachine(states=NOMES, transitions=transicoes, initial=inicial,
        auto_transitions=False, graph_engine="graphviz",
        title="Controle microprogramado: reset_1 tem prioridade em toda borda")


def avancar(maquina, start, ir, reset=0):
    # Este adaptador amostra entradas. Nao modela registradores do datapath.
    if reset:
        maquina.trigger("reset_1")
    elif maquina.state == "IDLE":
        maquina.trigger(f"start_{start}")
    elif maquina.state == "DECODE":
        maquina.trigger(f"ir_{ir}")
    else:
        maquina.trigger("borda")


def simular(opcode, a=5, b=7, inicial=0, mostrar=True):
    regs = construir_hardware()
    sim = pyrtl.Simulation(register_value_map={
        regs["r2"]: a, regs["r3"]: b, regs["r1"]: inicial})
    maquina = construir_maquina()
    linhas = []
    for ciclo in range(5):
        start = int(ciclo == 0)
        sim.step({"start": start, "reset": 0, "opcode": opcode})
        linha = {n: sim.inspect(n) for n in (
            "upc", "ir", "micro", "reg_write", "alu_sub", "alu_out",
            "r1", "r2", "r3", "pc", "pc_write", "done", "trap")}
        # Antes de avancar transitions, ambos mostram o estado deste ciclo.
        assert maquina.state == NOMES[linha["upc"]]
        avancar(maquina, start, linha["ir"])
        linhas.append(linha)
    if mostrar:
        print(f"\nOpcode={opcode}, R2={a}, R3={b}; estado antes da borda")
        print("ciclo estado  micro rw sub ULA  R1 done")
        for ciclo, x in enumerate(linhas):
            print(f'{ciclo:5} {NOMES[x["upc"]]:7} {x["micro"]:5}'
                  f' {x["reg_write"]:2} {x["alu_sub"]:3}'
                  f' {x["alu_out"]:3} {x["r1"]:3} {x["done"]:4}')
    return linhas


def verificar():
    assert ROM == [160, 64, 641, 643, 644, 8, 784, 784]
    for op, a, b, inicial in product(range(4), (0, 5, 250), (0, 7, 10), (0, 9)):
        t = simular(op, a, b, inicial, mostrar=False)
        esperado = (a + b) & 255 if op == 0 else (
            (a - b) & 255 if op == 1 else inicial)
        assert t[3]["r1"] == esperado
        assert t[3]["pc"] == (64 if op == 2 and inicial == 0 else 0)
        assert t[3]["trap"] == int(op == 3)
        assert t[3]["done"] == int(op != 3)
        assert [x["reg_write"] for x in t] == [0, 0, int(op < 2), 0, 0]
        assert all((x["r2"], x["r3"]) == (a, b) for x in t)
    # Todas as 128 combinacoes de estado/IR/start/reset: PyRTL x transitions.
    maquina = construir_maquina()
    for estado, ir, start, reset in product(range(8), range(4), range(2), range(2)):
        regs = construir_hardware()
        sim = pyrtl.Simulation(register_value_map={regs["upc"]: estado, regs["ir"]: ir})
        maquina.set_state(NOMES[estado])
        avancar(maquina, start, ir, reset)
        sim.step({"start": start, "reset": reset, "opcode": 0})
        assert sim.inspect("micro") == ROM[estado]
        if reset:
            assert sim.inspect("reg_write") == sim.inspect("pc_write") == 0
        sim.step({"start": 0, "reset": 0, "opcode": 0})
        assert NOMES[sim.inspect("upc")] == maquina.state
    print("Testes OK: 72 cenarios e 128 combinacoes de sequenciamento.")


def desenhar():
    # Diagrama gerado da propria GraphMachine; sem arestas automaticas to_X.
    maquina = construir_maquina()
    grafo = maquina.get_graph()
    grafo.attr(rankdir="LR", bgcolor="white", dpi="140")
    grafo.attr("node", fontname="DejaVu Sans", fontsize="11")
    grafo.attr("edge", fontname="DejaVu Sans", fontsize="9")
    base = Path(__file__).with_name("maquina_microprogramada_encontro6")
    for formato in ("svg", "png"):
        destino = base.with_suffix("." + formato)
        grafo.draw(str(destino), format=formato, prog="dot")
        print("Diagrama:", destino)


if __name__ == "__main__":
    print("endereco estado    palavra decimal hexadecimal")
    for endereco, valor in enumerate(ROM):
        print(f"{endereco:8} {NOMES[endereco]:9} {valor:010b} {valor:7} 0x{valor:03X}")
    simular(0)  # ADD: 641 = (5 << 7) | 1; R1 recebe 12.
    simular(1)  # SUB: 643 = (5 << 7) | 3; R1 recebe 254 (-2 em C2).
    verificar()
    desenhar()
