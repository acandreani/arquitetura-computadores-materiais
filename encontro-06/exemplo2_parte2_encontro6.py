"""Exemplo 2, parte 2: JZ e equivalencia dos controles em PyRTL.

Mantenha na mesma pasta encontro6_controle_pyrtl.py e
exemplo1_parte2_encontro6.py. Instale: pip install pyrtl transitions graphviz
O executavel Graphviz 'dot' tambem precisa estar no PATH.
Execute: python exemplo2_parte2_encontro6.py

Reutiliza os circuitos completos dos exemplos anteriores, evitando duas
definicoes divergentes de ROM. transitions desenha um recorte da execucao JZ;
as micro-operacoes e os registradores sao implementados em PyRTL.
"""
from pathlib import Path

import pyrtl
from transitions.extensions import GraphMachine

from encontro6_controle_pyrtl import montar
from exemplo1_parte2_encontro6 import construir_hardware, ROM, NOMES


def executar(tipo, opcode=2, r1_inicial=0, pc_inicial=0, reset_em=None):
    """Retorna sinais/estado ANTES da borda que encerra cada ciclo."""
    microprogramado = tipo == "microprogramado"
    if tipo not in ("cabeado", "microprogramado"):
        raise ValueError("tipo de controle invalido")
    regs = construir_hardware() if microprogramado else montar("cabeado")
    sim = pyrtl.Simulation(register_value_map={
        regs["r1"]: r1_inicial, regs["pc"]: pc_inicial,
        regs["r2"]: 5, regs["r3"]: 7})
    linhas = []
    for ciclo in range(5):
        reset = int(ciclo == reset_em)
        sim.step({"start": int(ciclo == 0), "reset": reset, "opcode": opcode})
        linha = {nome: sim.inspect(nome) for nome in (
            "ir", "r1", "r2", "r3", "pc", "reg_write", "alu_sub",
            "alu_out", "pc_write", "done", "trap")}
        linha["estado"] = sim.inspect("upc" if microprogramado else "estado")
        linha["reset"] = reset
        linha["zero"] = int(linha["r1"] == 0)
        if microprogramado:
            # Campos efetivamente lidos da ROM, nao valores esperados.
            linha["micro"] = sim.inspect("micro")
            linha["pc_req"] = (linha["micro"] >> 2) & 1
        linhas.append(linha)
    return linhas


def comparar(opcode=2, r1=0, pc=0, reset_em=None):
    cabeado = executar("cabeado", opcode, r1, pc, reset_em)
    micro = executar("microprogramado", opcode, r1, pc, reset_em)
    for a, b in zip(cabeado, micro):
        # Compara todos os campos comuns: estado, operandos, ULA e enables.
        assert a == {nome: b[nome] for nome in a}
        assert b["pc_write"] == (b["pc_req"] & b["zero"] & (1 - b["reset"]))
    return micro


def mostrar(linhas, r1):
    print(f"\nJZ 0x40, R1 inicial={r1}: "
          + ("desvio tomado" if r1 == 0 else "desvio nao tomado"))
    print("ciclo estado  micro pcReq Z reset pcWrite PC   R1 done")
    for ciclo, x in enumerate(linhas):
        print(f'{ciclo:5} {NOMES[x["estado"]]:7} {x["micro"]:5}'
              f' {x["pc_req"]:5} {x["zero"]:1} {x["reset"]:5}'
              f' {x["pc_write"]:7} 0x{x["pc"]:02X} {x["r1"]:2} {x["done"]:4}')


def verificar():
    assert ROM[4] == (5 << 7) | 4 == 644
    # Todos os valores possiveis de R1 e dois PCs iniciais; testa conservacao
    # de um PC nao nulo, para nao confundir conservar com zerar.
    for r1 in range(256):
        for pc in (0, 0x23):
            t = comparar(r1=r1, pc=pc)
            assert [x["estado"] for x in t] == [0, 1, 4, 5, 0]
            assert t[2]["micro"] == 644 and t[2]["pc_req"] == 1
            assert t[2]["pc"] == pc  # ainda antes da captura
            assert t[3]["pc"] == (0x40 if r1 == 0 else pc)
            assert [x["pc_write"] for x in t] == [0, 0, int(r1 == 0), 0, 0]
            assert [x["done"] for x in t] == [0, 0, 0, 1, 0]
            assert all(x["r1"] == r1 and x["reg_write"] == 0 for x in t)
    # Oito cenarios do exemplo do caderno: quatro opcodes e R1=0/9.
    for op in range(4):
        for r1 in (0, 9):
            comparar(opcode=op, r1=r1)
    # Reset tem prioridade sobre o salto, mesmo com Z=1.
    for r1 in (0, 9):
        t = comparar(r1=r1, pc=0x23, reset_em=2)
        assert t[2]["micro"] == 644 and t[2]["pc_req"] == 1
        assert t[2]["pc_write"] == 0
        assert t[3]["estado"] == t[3]["pc"] == t[3]["r1"] == 0
    print("Testes OK: 512 casos JZ, 8 casos de equivalencia e 2 de reset.")


def desenhar():
    maquina = GraphMachine(states=["IDLE", "DECODE", "JZ", "DONE"],
        transitions=[
            ["start=0", "IDLE", "IDLE"],
            ["start=1", "IDLE", "DECODE"],
            ["IR=2", "DECODE", "JZ"],
            ["borda (Z=0 ou Z=1)", "JZ", "DONE"],
            ["borda", "DONE", "IDLE"],
            ["reset=1", "*", "IDLE"]],
        initial="IDLE", auto_transitions=False, graph_engine="graphviz",
        title="JZ: recorte para opcode=2; reset tem prioridade em toda borda")
    # Confere a sequencia da maquina desenhada com o trace dos dois casos.
    for r1 in (0, 9):
        maquina.set_state("IDLE")
        estados = [maquina.state]
        for evento in ("start=1", "IR=2", "borda (Z=0 ou Z=1)", "borda"):
            maquina.trigger(evento)
            estados.append(maquina.state)
        assert estados == [NOMES[x["estado"]] for x in comparar(r1=r1)]
    maquina.set_state("IDLE")
    grafo = maquina.get_graph()
    grafo.attr(rankdir="TB", bgcolor="white", dpi="140")
    # Rotulos acrescentados ao grafo gerado por transitions: mostram as
    # acoes da ROM, em vez de apenas nomes abstratos dos estados.
    rotulos = {
        "IDLE": "0: IDLE | micro=160\nSe start=1: IR <- opcode\nAguardar ou seguir para 1",
        "DECODE": "1: DECODE | micro=64\nDespacho pelo IR\nIR=2: proximo endereco=4",
        "JZ": "4: JZ | micro=644 = (5 << 7) | 4\npcReq=1; reg_write=0; alvo=5\n"
              "pcWrite = pcReq & Z & ~reset\n"
              "Na borda, sem reset:\nZ=1: PC <- 0x40\nZ=0: PC conserva o valor\nR1 nao muda",
        "DONE": "5: DONE | micro=8\ndone=1; escritas desabilitadas\nPC ja reflete o resultado\nProximo endereco=0",
    }
    for nome, rotulo in rotulos.items():
        grafo.node(nome, label=rotulo, fontname="DejaVu Sans", fontsize="11")
    base = Path(__file__).with_name("maquina_jz_exemplo2_encontro6")
    for formato in ("png", "svg"):
        destino = base.with_suffix("." + formato)
        grafo.draw(str(destino), format=formato, prog="dot")
        print("Diagrama:", destino)


if __name__ == "__main__":
    print("JZ: ROM[4] = 644; pcReq=1; reg_write=0; alvo=5 (DONE).")
    for valor in (0, 9):
        mostrar(comparar(r1=valor), valor)
    verificar()
    desenhar()
