"""Verificacao das duas implementacoes e das fronteiras de ciclo."""
import pytest
import pyrtl
from itertools import product
from encontro6_controle_pyrtl import montar, simular


@pytest.mark.parametrize("op", range(4))
@pytest.mark.parametrize("a,b,inicial", [(5, 7, 0), (250, 10, 9),
                                       (0, 0, 0), (255, 255, 255)])
def test_equivalencia_e_resultados(op, a, b, inicial):
    ref = simular("cabeado", op, a, b, inicial)
    assert ref == simular("microprogramado", op, a, b, inicial)
    esperado = ((a + b) & 255) if op == 0 else (
        ((a - b) & 255) if op == 1 else inicial)
    assert ref[3]["r1"] == esperado
    assert ref[3]["pc"] == (64 if op == 2 and inicial == 0 else 0)
    assert sum(x["reg_write"] for x in ref) == (1 if op < 2 else 0)
    assert ref[3]["done"] == (op != 3)
    assert ref[3]["trap"] == (op == 3)


@pytest.mark.parametrize("tipo", ["cabeado", "microprogramado"])
def test_op_capturado_e_start_ocupado(tipo):
    regs = montar(tipo)
    sim = pyrtl.Simulation(register_value_map={regs["r2"]: 5, regs["r3"]: 7})
    for ciclo in range(5):
        sim.step({"start": int(ciclo < 3), "reset": 0,
                  "opcode": 0 if ciclo == 0 else 3})
        if ciclo in (1, 2, 3):
            assert sim.inspect("ir") == 0
        if ciclo == 3:
            assert sim.inspect("r1") == 12
            assert sim.inspect("done") == 1


@pytest.mark.parametrize("tipo", ["cabeado", "microprogramado"])
@pytest.mark.parametrize("estado", range(8))
def test_reset_e_estados_invalidos(tipo, estado):
    regs = montar(tipo)
    sim = pyrtl.Simulation(register_value_map={
        regs["estado"]: estado, regs["r1"]: 9, regs["pc"]: 64})
    sim.step({"start": 1, "reset": 1, "opcode": 0})
    assert sim.inspect("reg_write") == sim.inspect("pc_write") == 0
    sim.step({"start": 0, "reset": 0, "opcode": 0})
    assert sim.inspect("estado") == sim.inspect("r1") == sim.inspect("pc") == 0


@pytest.mark.parametrize("tipo", ["cabeado", "microprogramado"])
def test_estado7_e_trap_persistente(tipo):
    regs = montar(tipo)
    sim = pyrtl.Simulation(register_value_map={regs["estado"]: 7})
    for ciclo in range(4):
        sim.step({"start": 1, "reset": 0, "opcode": 0})
        assert sim.inspect("trap") == 1
        assert sim.inspect("reg_write") == sim.inspect("pc_write") == 0
        assert sim.inspect("estado") == (7 if ciclo == 0 else 6)


@pytest.mark.parametrize("tipo", ["cabeado", "microprogramado"])
def test_tabela_completa(tipo):
    for s, ir, start, z, reset in product(range(8), range(4), range(2),
                                         range(2), range(2)):
        regs = montar(tipo)
        ir_reg = pyrtl.working_block().get_wirevector_by_name("ir")
        sim = pyrtl.Simulation(register_value_map={
            regs["estado"]: s, ir_reg: ir, regs["r1"]: 0 if z else 1})
        destinos = [1 if start else 0, [2, 3, 4, 6][ir], 5, 5, 5, 0, 6, 6]
        sim.step({"start": start, "reset": reset, "opcode": 0})
        assert sim.inspect("reg_write") == int(s in (2, 3) and not reset)
        assert sim.inspect("pc_write") == int(s == 4 and z and not reset)
        sim.step({"start": 0, "reset": 0, "opcode": 0})
        assert sim.inspect("estado") == (0 if reset else destinos[s])


def test_128_cenarios():
    for op, a, b, inicial in product(range(4), (0, 1, 127, 255),
                                    (0, 1, 127, 255), (0, 9)):
        assert simular("cabeado", op, a, b, inicial) == simular(
            "microprogramado", op, a, b, inicial)


@pytest.mark.parametrize("tipo", ["cabeado", "microprogramado"])
def test_intervalo_aceitacoes(tipo):
    regs = montar(tipo)
    sim = pyrtl.Simulation()
    aceitos = []
    for ciclo in range(13):
        sim.step({"start": 1, "reset": 0, "opcode": 0})
        if sim.inspect("estado") == 0:
            aceitos.append(ciclo)
    assert aceitos == [0, 4, 8, 12]
