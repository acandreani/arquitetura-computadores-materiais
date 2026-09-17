"""Encontro 5 - Lista 1 - Exercicio 3.

Banco com quatro registradores de 8 bits, duas portas de leitura e uma porta
de escrita sincronizada pela borda do clock.
"""

import pyrtl


pyrtl.reset_working_block()

# Enderecos das duas portas de leitura.
src_a = pyrtl.Input(bitwidth=2, name="src_a")
src_b = pyrtl.Input(bitwidth=2, name="src_b")

# Sinais da porta de escrita.
dst = pyrtl.Input(bitwidth=2, name="dst")
write_data = pyrtl.Input(bitwidth=8, name="write_data")
write_enable = pyrtl.Input(bitwidth=1, name="write_enable")

registradores = [
    pyrtl.Register(bitwidth=8, name=f"r{i}")
    for i in range(4)
]

# Duas leituras combinacionais e independentes.
read_a = pyrtl.Output(bitwidth=8, name="read_a")
read_b = pyrtl.Output(bitwidth=8, name="read_b")
read_a <<= pyrtl.mux(src_a, *registradores)
read_b <<= pyrtl.mux(src_b, *registradores)

# Cada registrador recebe seu proprio circuito de selecao de escrita.
# Apenas o registrador cujo indice coincide com dst pode capturar write_data.
for indice, registrador in enumerate(registradores):
    selecionado = write_enable & (dst == indice)
    registrador.next <<= pyrtl.select(
        selecionado,
        falsecase=registrador,  # conserva o estado
        truecase=write_data,    # captura na borda
    )


def estado(simulacao: pyrtl.Simulation) -> list[int]:
    """Retorna os valores dos quatro registradores no ciclo observado."""
    return [simulacao.inspect(f"r{i}") for i in range(4)]


def executar_testes() -> None:
    valores_iniciais = [2, 4, 6, 8]
    mapa_inicial = {
        registrador: valor
        for registrador, valor in zip(registradores, valores_iniciais)
    }

    trace = pyrtl.SimulationTrace()
    simulacao = pyrtl.Simulation(
        tracer=trace,
        register_value_map=mapa_inicial,
    )

    # Ciclo 0: solicita R2 <- 0xAA.
    # Durante esta linha do trace, os registradores ainda mostram o estado
    # anterior a borda que encerra o ciclo.
    simulacao.step({
        "src_a": 2,
        "src_b": 0,
        "dst": 2,
        "write_data": 0xAA,
        "write_enable": 1,
    })
    assert estado(simulacao) == [2, 4, 6, 8]
    assert simulacao.inspect("read_a") == 6
    assert simulacao.inspect("read_b") == 2

    # Ciclo 1: a escrita anterior ja aparece no estado. Agora tentamos escrever
    # 0x55 em R1, mas com enable zero.
    simulacao.step({
        "src_a": 2,
        "src_b": 1,
        "dst": 1,
        "write_data": 0x55,
        "write_enable": 0,
    })
    estado_depois_da_escrita = estado(simulacao)
    assert estado_depois_da_escrita == [2, 4, 0xAA, 8]
    assert simulacao.inspect("read_a") == 0xAA
    assert simulacao.inspect("read_b") == 4

    # Ciclo 2: torna visivel o estado posterior a tentativa desabilitada.
    simulacao.step({
        "src_a": 1,
        "src_b": 2,
        "dst": 0,
        "write_data": 0,
        "write_enable": 0,
    })
    estado_depois_do_enable_zero = estado(simulacao)
    assert estado_depois_do_enable_zero == [2, 4, 0xAA, 8]

    # Compara cada posicao para provar que somente R2 mudou.
    indices_alterados = [
        indice
        for indice, (antes, depois) in enumerate(
            zip(valores_iniciais, estado_depois_da_escrita)
        )
        if antes != depois
    ]
    assert indices_alterados == [2]

    print("Estado inicial:                 ", valores_iniciais)
    print("Depois de R2 <- 0xAA:           ", estado_depois_da_escrita)
    print("Depois de enable=0 para R1:     ", estado_depois_do_enable_zero)
    print("Registradores alterados:        ", indices_alterados)
    print("\nTodos os testes passaram.\n")
    trace.render_trace(symbol_len=5)


if __name__ == "__main__":
    executar_testes()
