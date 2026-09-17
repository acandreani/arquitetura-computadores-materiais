"""Encontro 5 - Lista 1 - Exercicio 2.

Banco com quatro registradores de 8 bits e duas portas de leitura.
"""

import pyrtl


pyrtl.reset_working_block()

# Dois bits permitem selecionar um dos quatro registradores: 00, 01, 10 ou 11.
src_a = pyrtl.Input(bitwidth=2, name="src_a")
src_b = pyrtl.Input(bitwidth=2, name="src_b")

# Estado do banco de registradores.
registradores = [
    pyrtl.Register(bitwidth=8, name=f"r{i}")
    for i in range(4)
]

# Neste exercicio nao ha porta de escrita. Cada registrador conserva seu valor.
for registrador in registradores:
    registrador.next <<= registrador

# Cada porta possui seu proprio multiplexador e pode escolher uma fonte distinta.
valor_a = pyrtl.mux(src_a, *registradores)
valor_b = pyrtl.mux(src_b, *registradores)

read_a = pyrtl.Output(bitwidth=8, name="read_a")
read_b = pyrtl.Output(bitwidth=8, name="read_b")
read_a <<= valor_a
read_b <<= valor_b


def executar_testes() -> None:
    valores_iniciais = [2, 4, 6, 8]
    mapa_inicial = {
        registrador: valor
        for registrador, valor in zip(registradores, valores_iniciais)
    }

    simulacao = pyrtl.Simulation(register_value_map=mapa_inicial)

    print("src_a src_b | read_a read_b")
    print("------------+--------------")

    casos_testados = 0
    for endereco_a in range(4):
        for endereco_b in range(4):
            simulacao.step({"src_a": endereco_a, "src_b": endereco_b})

            observado_a = simulacao.inspect("read_a")
            observado_b = simulacao.inspect("read_b")
            esperado_a = valores_iniciais[endereco_a]
            esperado_b = valores_iniciais[endereco_b]

            assert observado_a == esperado_a
            assert observado_b == esperado_b

            print(
                f"  {endereco_a}     {endereco_b}  |"
                f"    {observado_a:2d}     {observado_b:2d}"
            )
            casos_testados += 1

    assert casos_testados == 16

    # As leituras sao combinacionais e nao devem modificar o estado.
    for indice, valor_esperado in enumerate(valores_iniciais):
        assert simulacao.inspect(f"r{indice}") == valor_esperado

    print(f"\n{casos_testados} combinacoes testadas com sucesso.")
    print("Estado final do banco: [2, 4, 6, 8]")


if __name__ == "__main__":
    executar_testes()
