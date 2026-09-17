# Arquitetura de Computadores — materiais para alunos

Materiais selecionados pelo professor Alexandre Cassimiro Andreani para a
disciplina de Arquitetura de Computadores, IFSP Câmpus Jacareí.

## Materiais disponíveis

Encontro 5, Lista 1 — soluções em Python/PyRTL:

- [Exercício 1: somador de oito bits](encontro-05/lista-01/solucao_encontro5_lista1_exercicio1.py)
- [Exercício 2: banco de registradores com duas leituras](encontro-05/lista-01/solucao_encontro5_lista1_exercicio2.py)
- [Exercício 3: porta de escrita e habilitação](encontro-05/lista-01/solucao_encontro5_lista1_exercicio3.py)

Encontro 6 — unidade de controle em PyRTL:

- [Exemplo resolvido 1: ADD com controle autônomo](encontro-06/exemplo_resolvido1_encontro6.py): máquina de estados, sinais de controle e trace ciclo a ciclo.
- [Controle cabeado e microprogramado](encontro-06/encontro6_controle_pyrtl.py): dois controladores para o mesmo caminho de dados, com simulação por ciclos.
- [Testes dos controladores](encontro-06/test_encontro6_controle_pyrtl.py): verificação de resultados, estados, reset, protocolo e equivalência.

## Como executar

Com Python 3.9 ou superior instalado, abra um terminal na pasta do repositório:

```bash
python -m venv .venv
```

Ative o ambiente com `source .venv/bin/activate` no Linux/macOS ou
`.venv\Scripts\activate` no Windows. Depois execute:

```bash
python -m pip install pyrtl pytest
python encontro-05/lista-01/solucao_encontro5_lista1_exercicio1.py
python encontro-05/lista-01/solucao_encontro5_lista1_exercicio2.py
python encontro-05/lista-01/solucao_encontro5_lista1_exercicio3.py
python encontro-06/exemplo_resolvido1_encontro6.py
python encontro-06/encontro6_controle_pyrtl.py
```

Cada solução inclui verificações automáticas e saída para acompanhamento.

Para executar a suíte de testes do encontro 6, na raiz do repositório:

```bash
python -m pytest -q encontro-06/test_encontro6_controle_pyrtl.py
```

## Seleção dos materiais

Este repositório recebe apenas materiais explicitamente escolhidos pelo
professor. A publicação é manual; não há sincronização automática com a pasta
de trabalho ou com o Google Drive. A presença de um arquivo nesses locais não
autoriza sua publicação aqui.

Novos materiais só serão adicionados após a decisão do professor.
