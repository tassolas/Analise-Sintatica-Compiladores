# Implementação da Análise Descendente (Analisador Preditivo)

**Instituição:** INSTITUTO FEDERAL GOIANO - Câmpus Trindade

**Curso:** Engenharia da Computação

**Disciplina:** Compiladores

**Professor:** Gomide

**Aluno(s):** Tássio Moraes, Lucas, Rafael 

## 💻 Sobre o Projeto

Este projeto consiste na implementação de um programa de Análise Sintática Descendente. O objetivo principal é construir um analisador preditivo que valide comandos léxicos com base em uma gramática livre de contexto pré-definida.

A arquitetura do analisador é composta por:
* Um buffer de entrada para realizar a leitura das instruções.
* Uma pilha para armazenar a sequência de símbolos da gramática.
* Uma tabela de análise (Tabela M).
* Um fluxo de saída para exportar o log de validação.

## 📚 Gramática e Dicionário

O algoritmo foi desenvolvido para consumir obrigatoriamente um dicionário de dados específico que contém os elementos *first*, *follow*, terminais e não-terminais. A gramática empregada no projeto é apresentada a seguir:

* $E\rightarrow TX$
* $X\rightarrow+TX|\epsilon$
* $T\rightarrow FY$
* $Y\rightarrow*FY|\epsilon$
* $F\rightarrow(E)|id$

## ⚙️ Como Executar e Testar

1.  **Entrada de Dados:** O programa lê um arquivo de texto onde cada linha representa uma instrução a ser analisada.
2.  **Processamento:** O algoritmo realiza a análise sintática descendente de todos os comandos fornecidos.
3.  **Geração de Saída:** Ao finalizar, é gerado um arquivo de texto de saída. Este arquivo contém:
    * A expressão original de entrada.
    * O status informando se o comando é válido.
    * A demonstração da execução da pilha passo a passo.

## 🚀 Tecnologias Utilizadas

* **Linguagem:** Python (py)
* **Ambiente:** Vscode
