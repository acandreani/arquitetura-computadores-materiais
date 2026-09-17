"""Encontro 5 - Lista 1 - Exercicio 1.

Somador combinacional de 8 bits em PyRTL.
"""

import pyrtl


pyrtl.reset_working_block()

# Duas entradas de 8 bits representam as entradas do somador.
a = pyrtl.Input(bitwidth=8, name="a")
b = pyrtl.Input(bitwidth=8, name="b")

# Em PyRTL, a soma de duas palavras de 8 bits produz 9 bits para preservar
# o carry. O resultado arquitetural conserva apenas os 8 bits inferiores.
soma_completa = a + b
soma_8bits = soma_completa[:8]
carry = soma_completa[8]

resultado = pyrtl.Output(bitwidth=8, name="resultado")
carry_out = pyrtl.Output(bitwidth=1, name="carry_out")
resultado <<= soma_8bits
carry_out <<= carry


def executar_testes() -> None:
    trace = pyrtl.SimulationTrace()
    simulacao = pyrtl.Simulation(tracer=trace)

    casos = [
        # a, b, resultado esperado, carry esperado
        (5, 7, 12, 0),
        (250, 10, 4, 1),
    ]

    for valor_a, valor_b, esperado, carry_esperado in casos:
        simulacao.step({"a": valor_a, "b": valor_b})

        observado = simulacao.inspect("resultado")
        carry_observado = simulacao.inspect("carry_out")

        assert observado == esperado
        assert carry_observado == carry_esperado

        soma_inteira = valor_a + valor_b
        print(
            f"{valor_a:3d} + {valor_b:3d} = {soma_inteira:3d}; "
            f"resultado de 8 bits = {observado:3d} "
            f"(0x{observado:02X}); carry = {carry_observado}"
        )

    print("\nTodos os testes passaram.\n")
    trace.render_trace(symbol_len=5)


if __name__ == "__main__":
    executar_testes()
