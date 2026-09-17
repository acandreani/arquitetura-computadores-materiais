"""Encontro 6: mesmo caminho de dados, controle cabeado ou microprogramado.

Execute: python encontro6_controle_pyrtl.py
Os valores do trace pertencem ao inicio do ciclo, antes da captura seguinte.
"""
import pyrtl

IDLE, DECODE, ADD, SUB, JZ, DONE, TRAP = range(7)


def montar(tipo="cabeado"):
    if tipo not in ("cabeado", "microprogramado"):
        raise ValueError("tipo de controle invalido")
    pyrtl.reset_working_block()
    start = pyrtl.Input(1, "start")
    reset = pyrtl.Input(1, "reset")
    opcode = pyrtl.Input(2, "opcode")
    estado = pyrtl.Register(3, "estado")
    ir = pyrtl.Register(2, "ir")
    r1 = pyrtl.Register(8, "r1")
    r2 = pyrtl.Register(8, "r2")
    r3 = pyrtl.Register(8, "r3")
    pc = pyrtl.Register(8, "pc")
    z = r1 == 0
    aceitar = (estado == IDLE) & start
    ir.next <<= pyrtl.select(reset, 0,
        pyrtl.select(aceitar, opcode, ir))
    despacho = pyrtl.mux(ir, ADD, SUB, JZ, TRAP)

    if tipo == "cabeado":
        rw = (estado == ADD) | (estado == SUB)
        sub = estado == SUB
        pw = estado == JZ
        fim = estado == DONE
        erro = (estado == TRAP) | (estado == 7)
        prox = pyrtl.mux(estado,
            pyrtl.select(start, DECODE, IDLE),
            despacho, DONE, DONE, DONE, IDLE, TRAP, TRAP)
    else:
        # Bits: [9:7] alvo, [6:5] modo, [4] trap, [3] done,
        #       [2] pc_req, [1] alu_sub, [0] reg_write.
        # Modo 0: alvo; 1: aguardar start; 2: despacho por IR.
        def palavra(alvo, modo=0, rw=0, sub=0, pw=0, fim=0, erro=0):
            return ((alvo << 7) | (modo << 5) | (erro << 4)
                    | (fim << 3) | (pw << 2) | (sub << 1) | rw)

        conteudo = [
            palavra(DECODE, modo=1), palavra(0, modo=2),
            palavra(DONE, rw=1), palavra(DONE, rw=1, sub=1),
            palavra(DONE, pw=1), palavra(IDLE, fim=1),
            palavra(TRAP, erro=1), palavra(TRAP, erro=1)]
        rom = pyrtl.RomBlock(10, 3, conteudo, name="controle")
        micro = rom[estado]
        rw, sub, pw, fim, erro = [micro[i] for i in range(5)]
        modo, alvo = micro[5:7], micro[7:10]
        prox = pyrtl.mux(modo, alvo,
            pyrtl.select(start, alvo, IDLE), despacho, TRAP)

    # As duas unidades comandam exatamente o mesmo caminho de dados.
    we = rw & ~reset
    pc_we = pw & z & ~reset
    resultado = pyrtl.select(sub, (r2 - r3)[:8], (r2 + r3)[:8])
    estado.next <<= pyrtl.select(reset, IDLE, prox)
    r1.next <<= pyrtl.select(reset, 0, pyrtl.select(we, resultado, r1))
    r2.next <<= r2
    r3.next <<= r3
    pc.next <<= pyrtl.select(reset, 0, pyrtl.select(pc_we, 0x40, pc))
    for nome, sinal in [("reg_write", we), ("alu_sub", sub),
                        ("pc_write", pc_we), ("zero", z),
                        ("done", fim & ~reset), ("trap", erro & ~reset),
                        ("alu_out", resultado)]:
        saida = pyrtl.Output(len(sinal), nome)
        saida <<= sinal
    return {"estado": estado, "r1": r1, "r2": r2, "r3": r3, "pc": pc}


def simular(tipo="cabeado", op=0, a=5, b=7, inicial=0):
    regs = montar(tipo)
    sim = pyrtl.Simulation(register_value_map={
        regs["r2"]: a, regs["r3"]: b, regs["r1"]: inicial})
    linhas = []
    for ciclo in range(5):
        sim.step({"start": int(ciclo == 0), "reset": 0, "opcode": op})
        nomes = ("estado", "ir", "r1", "pc", "reg_write",
                 "alu_sub", "pc_write", "done", "trap", "alu_out")
        linhas.append({nome: sim.inspect(nome) for nome in nomes})
    return linhas


if __name__ == "__main__":
    for tipo in ("cabeado", "microprogramado"):
        trace = simular(tipo)
        assert [x["estado"] for x in trace] == [0, 1, 2, 5, 0]
        assert trace[2]["r1"] == 0 and trace[3]["r1"] == 12
        print(tipo)
        for ciclo, linha in enumerate(trace):
            print(ciclo, linha)
