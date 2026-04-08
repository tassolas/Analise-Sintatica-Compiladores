import re
import os

# =====================================================================================
#  MÓDULOS IMPORTADOS
# =====================================================================================
# `re` (Regular Expressions): Biblioteca padrão do Python para busca de padrões em texto.
#      Usaremos `re.finditer` e `re.findall` para tokenizar a entrada e dividir produções.
#
# `os` (Operating System): Biblioteca padrão para interagir com o sistema de arquivos.
#      Usaremos apenas `os.path.exists` para verificar se o arquivo de entrada já existe
#      antes de tentar criá-lo automaticamente.


# =====================================================================================
#  ESTRUTURA DE DADOS: O CÉREBRO DO ANALISADOR (Dicionário 'linguagem')
# =====================================================================================
# POR QUE EXISTE: Um analisador LL(1) precisa de uma gramática livre de contexto (GLC)
# devidamente fatorada (sem ambiguidade) e sem recursão à esquerda. Este dicionário
# centraliza todas as informações dessa gramática em um único lugar.
#
# POR QUE UM DICIONÁRIO: Dicionários Python têm acesso O(1) por chave (tabela hash),
# o que é ideal para consultas repetidas durante a análise. Alternativas como listas
# de tuplas teriam acesso O(n), tornando o parser mais lento sem ganho algum.
#
# POR QUE HARDCODADO: Hardcodar (escrever direto no código) a tabela evita que tenhamos
# que implementar os algoritmos de cálculo de FIRST, FOLLOW e construção da Tabela M em
# tempo de execução — o que, embora didático, faria o código ser várias vezes maior.
linguagem = {

    # ----------------------------------------------------------------------------------
    # "terminal": Lista de todos os símbolos terminais da gramática.
    # ----------------------------------------------------------------------------------
    # Terminais são os tokens atômicos que vêm diretamente da entrada do usuário.
    # Eles NÃO podem ser expandidos — são as "folhas" da árvore sintática.
    #
    # '+' → operador de adição
    # '*' → operador de multiplicação
    # '(' → abre parêntese
    # ')' → fecha parêntese
    # 'id' → identificador genérico (representa qualquer nome de variável ou número)
    # '$' → marcador especial de fim de cadeia (EOF). É o sentinela que indica ao
    #        algoritmo que a entrada foi completamente consumida.
    "terminal": ['+', '*', '(', ')', 'id', '$'],

    # ----------------------------------------------------------------------------------
    # "nonterminal": Lista de todos os símbolos não-terminais da gramática.
    # ----------------------------------------------------------------------------------
    # Não-terminais são variáveis sintáticas — abstrações que PRECISAM ser substituídas
    # (expandidas) por sequências de terminais e/ou outros não-terminais, seguindo as
    # regras da gramática, até que só restem terminais.
    #
    # E → Expressão   (Expression): raiz da gramática, representa a expressão inteira.
    # X → Continuação da expressão após o primeiro termo (lida com o '+').
    # T → Termo       (Term): representa um fator ou produto de fatores.
    # Y → Continuação do termo (lida com o '*').
    # F → Fator       (Factor): unidade mínima — um 'id' ou uma sub-expressão entre '()'.
    "nonterminal": ['E', 'X', 'T', 'Y', 'F'],

    # ----------------------------------------------------------------------------------
    # "gramar": As regras de produção da gramática (o conjunto de substituições).
    # ----------------------------------------------------------------------------------
    # Cada chave é um não-terminal. O valor é a lista de produções possíveis para ele.
    # 'null' representa Épsilon (ε) — a produção vazia, ou seja, o não-terminal pode
    # simplesmente desaparecer sem gerar nenhum símbolo.
    #
    # Lendo as regras:
    #   E  → TX        (uma expressão é sempre um Termo seguido de X)
    #   X  → +TX | ε   (X pode ser '+' seguido de outro Termo e X, ou desaparecer)
    #   T  → FY        (um Termo é sempre um Fator seguido de Y)
    #   Y  → *FY | ε   (Y pode ser '*' seguido de outro Fator e Y, ou desaparecer)
    #   F  → (E) | id  (um Fator é uma sub-expressão entre parênteses, ou um identificador)
    #
    # Nota: X e Y existem para eliminar a recursão à esquerda e garantir que a gramática
    # seja LL(1). Sem eles, teríamos E → E+T, que quebraria qualquer parser descendente.
    "gramar": {
        "E": ['TX'],
        "X": ['+TX', 'null'],
        "T": ['FY'],
        "Y": ['*FY', 'null'],
        "F": ['(E)', 'id']
    },

    # ----------------------------------------------------------------------------------
    # "first": Conjuntos FIRST de cada não-terminal.
    # ----------------------------------------------------------------------------------
    # FIRST(A) = conjunto de terminais que podem aparecer como o PRIMEIRO símbolo
    # em qualquer string derivada a partir de A.
    # Se A pode derivar ε (vazio), então 'null' também entra no FIRST(A).
    #
    # Exemplo: FIRST(E) = {'(', 'id'} porque toda expressão começa com '(' ou 'id'.
    # Exemplo: FIRST(X) = {'+', null} porque X começa com '+', ou some (ε).
    #
    # ATENÇÃO: Este campo existe apenas para documentar a gramática e facilitar a
    # conferência da Tabela M. O algoritmo de análise em si usa diretamente a tableM.
    "first": {
        "E": ['(', 'id'], "X": ['+', 'null'], "T": ['(', 'id'],
        "Y": ['*', 'null'], "F": ['(', 'id']
    },

    # ----------------------------------------------------------------------------------
    # "follow": Conjuntos FOLLOW de cada não-terminal.
    # ----------------------------------------------------------------------------------
    # FOLLOW(A) = conjunto de terminais que podem aparecer IMEDIATAMENTE APÓS A
    # em qualquer forma sentencial derivada a partir do símbolo inicial.
    # '$' sempre entra no FOLLOW do símbolo inicial (E), pois ele pode ser o último.
    #
    # Exemplo: FOLLOW(E) = {')', '$'} — E pode ser seguido de ')' (dentro de parênteses)
    # ou de '$' (quando é a expressão completa).
    #
    # Estes conjuntos são usados para preencher as entradas de ε (null) na Tabela M:
    # quando A → ε, colocamos essa produção em M[A][b] para todo b ∈ FOLLOW(A).
    #
    # ATENÇÃO: Assim como "first", este campo serve para documentação e conferência.
    "follow": {
        "E": [')', '$'], "X": [')', '$'], "T": ['+', ')', '$'],
        "Y": ['+', ')', '$'], "F": ['*', '+', ')', '$']
    },

    # ----------------------------------------------------------------------------------
    # "tableM": A Tabela de Análise Preditiva LL(1) — o coração do algoritmo.
    # ----------------------------------------------------------------------------------
    # POR QUE EXISTE: O analisador precisa "prever" (por isso "preditivo") qual regra
    # de produção usar olhando apenas 1 token à frente na entrada (daí o "1" do LL(1)).
    # Sem essa tabela, o parser teria que tentar todas as produções possíveis (backtracking),
    # tornando-o exponencialmente mais lento.
    #
    # COMO LER: tableM[NÃO-TERMINAL][TOKEN_ATUAL] = 'PRODUÇÃO A USAR'
    #
    # Exemplo: tableM['E']['id'] = 'TX'
    #   → Se o topo da pilha é 'E' e o próximo token é 'id', use a regra E → TX.
    #
    # Exemplo: tableM['X']['$'] = 'null'
    #   → Se o topo da pilha é 'X' e o próximo token é '$' (fim da entrada), use X → ε.
    #     Isso faz X desaparecer sem consumir nenhum token.
    #
    # ERRO SINTÁTICO: Se a combinação [não-terminal][token] NÃO existir na tabela
    # (ex: tableM['F']['+']), significa que a entrada tem um erro de sintaxe — o usuário
    # escreveu algo que a gramática não consegue derivar.
    #
    # COMO FOI CONSTRUÍDA: Cada entrada M[A][a] = α é preenchida quando:
    #   1. a ∈ FIRST(α)  → o token 'a' inicia a produção α, então use-a.
    #   2. ε ∈ FIRST(α) e a ∈ FOLLOW(A) → α pode ser vazia e 'a' vem depois de A.
    "tableM": {
        "E": {'id': 'TX',   '(':  'TX'},
        "X": {'+':  '+TX',  ')':  'null', '$': 'null'},
        "T": {'id': 'FY',   '(':  'FY'},
        "Y": {'+':  'null', '*':  '*FY', ')': 'null', '$': 'null'},
        "F": {'id': 'id',   '(':  '(E)'}
    }
}


# =====================================================================================
#  ANALISADOR LÉXICO — tokenize(line)
# =====================================================================================
# RESPONSABILIDADE: Converter uma string de texto bruto (ex: "a + b * c") em uma lista
# de tokens que a gramática entende (ex: ['id', '+', 'id', '*', 'id', '$']).
# Isso é a "Análise Léxica" — o primeiro estágio de qualquer compilador.
#
# POR QUE É NECESSÁRIO: O analisador sintático (parse) opera sobre símbolos abstratos
# definidos na gramática. Ele não sabe o que fazer com uma letra 'a' ou o número '42'
# diretamente — mas sabe o que fazer com o token genérico 'id', que representa qualquer
# um desses identificadores.
#
# COMO FUNCIONA:
#   1. `re.finditer` varre a string da esquerda para a direita.
#   2. A cada trecho encontrado, decide se é um operador (mantém como está)
#      ou um identificador/número (converte para 'id').
#   3. Ao final, adiciona '$' para sinalizar o fim da cadeia.
def tokenize(line):
    tokens = []

    # re.finditer retorna um iterador com todos os trechos que casam com o padrão,
    # na ordem em que aparecem na string, sem sobreposição.
    #
    # O padrão r'\+|\*|\(|\)|\w+' é lido como:
    #   \+   → um símbolo de '+' literal (escapado pois '+' tem significado especial em regex)
    #   |    → OU
    #   \*   → um símbolo de '*' literal
    #   |    → OU
    #   \(   → um '(' literal
    #   |    → OU
    #   \)   → um ')' literal
    #   |    → OU
    #   \w+  → uma ou mais letras, dígitos ou underline (padrão de identificador)
    #
    # A ORDEM IMPORTA: os operadores vêm antes de \w+ porque o regex tenta as
    # alternativas da esquerda para a direita. Como operadores são só 1 caractere,
    # não haveria conflito, mas manter essa ordem é boa prática.
    for match in re.finditer(r'\+|\*|\(|\)|\w+', line):
        tok = match.group()  # .group() retorna o trecho de texto que casou com o padrão.

        # DECISÃO DE CLASSIFICAÇÃO:
        # - `tok.isalnum()` → True se tok contém APENAS letras e dígitos (ex: "var1", "42").
        # - `'_' in tok`    → True se tok contém underline (ex: "minha_var").
        #   Nota: `isalnum()` sozinho retorna False para strings com '_', por isso
        #   a segunda condição é necessária para cobrir identificadores com underline.
        # - Se qualquer uma das condições for True, é um identificador → converte para 'id'.
        # - Caso contrário, é um operador ou pontuação → mantém o caractere original.
        tokens.append('id' if tok.isalnum() or '_' in tok else tok)

    # Adiciona o marcador de fim de cadeia.
    # SEM ELE: o loop `while True` dentro de `parse` tentaria acessar tokens[ptr]
    # além do fim da lista, gerando um IndexError (crash). Com ele, o algoritmo
    # tem uma condição de parada clara e segura.
    tokens.append('$')
    return tokens


# =====================================================================================
#  DIVISOR DE PRODUÇÕES — split_production(prod)
# =====================================================================================
# RESPONSABILIDADE: Receber uma string de produção (ex: "+TX", "(E)", "*FY", "id")
# e devolvê-la como uma lista de símbolos individuais (ex: ['+','T','X'], ['(','E',')'],
# ['*','F','Y'], ['id']).
#
# POR QUE NÃO USAR list() OU split():
#   - `list("TX")`  → ['T', 'X']  ✓ funciona para símbolos de 1 caractere.
#   - `list("id")`  → ['i', 'd']  ✗ QUEBRA — 'i' e 'd' não são símbolos da gramática!
#   - `list("(E)")` → ['(', 'E', ')']  ✓ funcionaria, mas não genericamente.
#   O problema central é o token 'id', que tem 2 caracteres mas representa 1 símbolo.
#   Por isso usamos regex, que consegue reconhecê-lo como unidade atômica.
#
# COMO FUNCIONA:
#   `re.findall` retorna uma lista com todos os trechos que casam, na ordem.
#   O padrão r'id|[+*()\w]' é lido como:
#     id         → a palavra literal "id" (tem prioridade por vir primeiro)
#     |          → OU
#     [+*()\w]   → qualquer único caractere que seja +, *, (, ), ou \w (letra/dígito)
#
#   Ordem importa: 'id' é tentado ANTES de \w, então quando encontra "id" na string,
#   ele captura os dois caracteres juntos em vez de capturar 'i' e depois 'd' separados.
def split_production(prod):
    return re.findall(r'id|[+*()\w]', prod)


# =====================================================================================
#  FORMATADOR VISUAL DA PILHA — fmt(stack)
# =====================================================================================
# RESPONSABILIDADE: Receber a pilha interna (uma lista Python) e devolver uma string
# formatada como "[A, B, C]" para ser gravada no arquivo de saída a cada passo.
#
# POR QUE FILTRAR '$':
#   O '$' é um sentinela técnico do algoritmo — ele existe para marcar o fundo da pilha
#   e permitir a detecção da condição de aceitação (quando topo == '$'). Ele é um
#   detalhe de implementação, não um símbolo da gramática que o usuário precisa ver.
#   Filtrá-lo deixa a saída mais limpa e fiel ao que os livros de compiladores mostram.
#
# CONVENÇÃO DE EXIBIÇÃO (fundo → topo):
#   Internamente, a pilha usa o índice -1 como topo (último elemento).
#   Ex: stack = ['$', 'E', 'T', 'X'] → topo é 'X', fundo é '$'.
#   Após filtrar '$': visible = ['E', 'T', 'X'] → exibe como "[E, T, X]".
#   Isso significa que o topo da pilha aparece à DIREITA na exibição,
#   convenção usada nos exemplos do enunciado.
def fmt(stack):
    visible = [s for s in stack if s != '$']
    return '[' + ', '.join(visible) + ']'


# =====================================================================================
#  NÚCLEO: ANALISADOR PREDITIVO LL(1) — parse(tokens)
# =====================================================================================
# RESPONSABILIDADE: Receber a lista de tokens produzida por `tokenize` e determinar
# se ela pertence à linguagem definida pela gramática. Ao mesmo tempo, registra
# cada estado da pilha para gerar o relatório passo a passo.
#
# MODELO TEÓRICO — Autômato com Pilha Determinístico (APD):
#   O parser LL(1) é formalmente um APD. Ele possui:
#     - Uma FITA de entrada (a lista `tokens`), lida da esquerda para a direita.
#     - Uma PILHA de símbolos, manipulada pelo algoritmo.
#     - Uma TABELA DE TRANSIÇÃO (tableM), que dita o que fazer em cada situação.
#   A cada passo, ele olha o topo da pilha + 1 token da fita → decide a ação.
#
# DOIS TIPOS DE AÇÃO:
#   1. MATCH (casamento): topo é terminal == token atual → consome ambos.
#   2. EXPANSÃO: topo é não-terminal → substitui pelo lado direito da produção.
#
# RECUPERAÇÃO DE ERROS (Panic Mode simplificado):
#   Quando um erro é detectado, em vez de abortar, o parser descarta o topo da pilha
#   e continua. Isso permite processar a pilha até o fim mesmo com entrada inválida,
#   gerando um histórico completo de estados para depuração.
def parse(tokens):

    # Referências locais: extraímos as sub-estruturas do dicionário para variáveis
    # com nomes curtos, evitando escrever linguagem["tableM"] repetidamente no loop.
    table  = linguagem["tableM"]
    terms  = linguagem["terminal"]
    nterms = linguagem["nonterminal"]

    # ----------------------------------------------------------------------------------
    # INICIALIZAÇÃO DA PILHA
    # ----------------------------------------------------------------------------------
    # A pilha começa com dois elementos:
    #   '$' no fundo (índice 0): sentinela — nunca é removido até a aceitação final.
    #   'E' no topo (índice -1): símbolo inicial da gramática — toda análise começa aqui.
    #
    # Em Python, usamos uma lista onde o ÚLTIMO elemento (índice -1) é o TOPO.
    # Operações de pilha:
    #   stack.append(x)  → empilha (push)
    #   stack.pop()      → desempilha (pop) do topo
    #   stack[-1]        → espia o topo (peek) sem remover
    stack = ['$', 'E']

    # ----------------------------------------------------------------------------------
    # HISTÓRICO DE ESTADOS
    # ----------------------------------------------------------------------------------
    # `states` guarda uma "fotografia" da pilha após cada operação significativa.
    # O estado inicial (pilha com apenas 'E') já é registrado antes do loop começar.
    # Ao final, essa lista será usada por `format_output` para gerar o relatório.
    states = [fmt(stack)]

    # ----------------------------------------------------------------------------------
    # PONTEIRO DE LEITURA E FLAG DE VALIDADE
    # ----------------------------------------------------------------------------------
    # `ptr` aponta para o token atual na lista de entrada. Começa em 0 (primeiro token).
    # Avança (ptr += 1) apenas quando um terminal é consumido por casamento (match).
    #
    # `valid` começa como True (otimismo). É setado para False na primeira detecção
    # de erro e nunca volta para True. Ao final, indica se a expressão é válida.
    ptr   = 0
    valid = True

    # ==================================================================================
    # LOOP PRINCIPAL DO ALGORITMO
    # ==================================================================================
    # Este loop executa uma iteração por operação de pilha.
    # Ele NÃO tem `break` em caso de erro — continua até pilha e entrada se esgotarem.
    # O único `break` legítimo é a condição de aceitação (ambos chegam ao '$').
    # Garantia de terminação: cada iteração SEMPRE remove ao menos 1 elemento da pilha
    # ou avança o ponteiro, então o loop obrigatoriamente termina em tempo finito.
    while True:

        # Espiamos o topo sem remover. stack[-1] = último elemento da lista = topo.
        top = stack[-1]

        # ------------------------------------------------------------------------------
        # CONDIÇÃO DE PARADA E ACEITAÇÃO
        # ------------------------------------------------------------------------------
        # Quando AMBAS as condições são verdadeiras simultaneamente:
        #   - top == '$': a pilha foi completamente esvaziada (só resta o sentinela).
        #   - tokens[ptr] == '$': toda a entrada foi consumida (chegamos ao EOF).
        # Isso significa que a gramática derivou exatamente a sequência de tokens
        # fornecida — aceitação bem-sucedida (se `valid` ainda for True).
        #
        # O `if fmt(stack) != '[]'` garante que o estado final '[]' seja registrado
        # exatamente uma vez, mesmo que o loop tenha chegado até aqui de formas
        # diferentes dependendo da expressão.
        if top == '$' and tokens[ptr] == '$':
            if fmt(stack) != '[]':
                stack.pop()
                states.append(fmt(stack))
            break  # ÚNICO break do loop. Encerra a análise.

        # Token atual da fita de entrada (o "lookahead" do LL(1)).
        token = tokens[ptr]

        # ==============================================================================
        # CASO 1: TOPO DA PILHA É UM TERMINAL
        # ==============================================================================
        # Se o topo é um terminal, só existe uma ação possível: tentar casar com o token.
        # Não há consulta à tabela — terminais precisam ser igualados diretamente.
        if top in terms:

            if top == token:
                # ------- MATCH (Casamento bem-sucedido) -------
                # O terminal esperado (topo da pilha) é igual ao token lido da entrada.
                # Ação: consumimos ambos.
                #   stack.pop() → remove o terminal da pilha (foi "satisfeito").
                #   ptr += 1    → avança para o próximo token da entrada.
                # Após isso, registramos o novo estado da pilha.
                stack.pop()
                ptr += 1
                states.append(fmt(stack))

            else:
                # ------- ERRO: terminal incompatível -------
                # A pilha esperava um símbolo específico (ex: ')'), mas chegou outro (ex: '+').
                # Exemplo concreto: expressão "(id+id" — quando chegar em ')' esperado
                # mas a entrada já está em '$', ocorre este erro.
                #
                # RECUPERAÇÃO (Panic Mode): descartamos o terminal do topo da pilha.
                # NÃO avançamos o ponteiro — o token problemático pode ainda casar
                # com algo mais abaixo na pilha.
                valid = False
                stack.pop()
                states.append(fmt(stack))

        # ==============================================================================
        # CASO 2: TOPO DA PILHA É UM NÃO-TERMINAL
        # ==============================================================================
        # Se o topo é um não-terminal, precisamos expandi-lo (substituí-lo pela produção
        # correta). Qual produção usar? Consultamos a Tabela M.
        elif top in nterms:

            # `table.get(top, {})`: retorna a linha da tabela para o não-terminal `top`.
            # O segundo argumento `{}` é o valor padrão caso `top` não exista na tabela
            # (nunca acontece com nossa gramática, mas é uma boa prática defensiva).
            row = table.get(top, {})

            if token not in row:
                # ------- ERRO: sem regra na tabela -------
                # A combinação (não-terminal no topo, token atual) não tem entrada na
                # Tabela M. Isso significa que a gramática não prevê essa situação —
                # a entrada é sintaticamente inválida nesse ponto.
                # Exemplo: topo é 'F' e token é '+' → tableM['F'] não tem chave '+'.
                #
                # RECUPERAÇÃO: descartamos o não-terminal do topo da pilha.
                # O token permanece na entrada para ser comparado com o próximo topo.
                valid = False
                stack.pop()
                states.append(fmt(stack))

            else:
                # ------- SUCESSO NA CONSULTA: expandindo o não-terminal -------
                # Encontramos a produção a usar: production = tableM[top][token].
                production = row[token]

                # Removemos o não-terminal do topo — ele será substituído pelos
                # símbolos da produção que vamos empilhar a seguir.
                stack.pop()

                if production == 'null':
                    # ---- PRODUÇÃO ÉPSILON (ε) ----
                    # O não-terminal deriva a string vazia — simplesmente desaparece.
                    # Semanticamente, bastaria fazer stack.pop() (já feito acima) e seguir.
                    #
                    # Porém, para fins didáticos e para bater com o formato de saída
                    # exigido pelo enunciado, fazemos dois registros extras:
                    #   1. Empilhamos 'null' e registramos → mostra [... null] no histórico.
                    #   2. Desempilhamos 'null' e registramos → mostra o estado sem ele.
                    # Isso torna visível ao usuário que uma transição ε ocorreu.
                    stack.append('null')
                    states.append(fmt(stack))   # estado com 'null' visível
                    stack.pop()
                    states.append(fmt(stack))   # estado após remover 'null'

                else:
                    # ---- PRODUÇÃO NORMAL: expansão na pilha ----
                    # Dividimos a string de produção nos seus símbolos constituintes.
                    # Ex: 'TX' → ['T', 'X'] | '+TX' → ['+', 'T', 'X'] | '(E)' → ['(','E',')']
                    symbols = split_production(production)

                    # POR QUE `reversed`?
                    # A pilha é LIFO: o último a entrar é o primeiro a sair.
                    # Queremos que o PRIMEIRO símbolo da produção seja processado PRIMEIRO,
                    # logo ele precisa estar no TOPO (último empilhado).
                    #
                    # Exemplo com produção 'TX':
                    #   symbols = ['T', 'X']
                    #   reversed → empilhamos 'X' primeiro, depois 'T'.
                    #   Estado final da pilha: [..., 'X', 'T'] → topo é 'T'. ✓
                    #
                    # Se empilhássemos na ordem normal ('T' primeiro, depois 'X'),
                    # o topo seria 'X', e processaríamos X antes de T — erro de derivação.
                    for sym in reversed(symbols):
                        stack.append(sym)

                    # Registra o novo estado da pilha após a expansão.
                    states.append(fmt(stack))

        # ==============================================================================
        # CASO 3: TOPO DESCONHECIDO (SALVAGUARDA ARQUITETURAL)
        # ==============================================================================
        # Este bloco só é alcançado se o topo não for terminal nem não-terminal.
        # Na prática, o único símbolo que pode chegar aqui é 'null' residual — ocorre
        # quando, em alguma situação de erro, um 'null' não foi removido no momento certo.
        # 'null' não é terminal nem não-terminal, então cai aqui.
        #
        # Descartamos o topo para garantir que o loop continue avançando e não trave.
        else:
            valid = False
            stack.pop()
            states.append(fmt(stack))

    # Retorna uma tupla com:
    #   valid  → True se a expressão pertence à linguagem, False se há erro sintático.
    #   states → lista de strings com o histórico completo de estados da pilha.
    return valid, states


# =====================================================================================
#  GERADOR DE RELATÓRIO — format_output(expr, valid, states)
# =====================================================================================
# RESPONSABILIDADE: Montar o bloco de texto formatado para uma única expressão,
# no padrão exigido pelo enunciado:
#
#   Input: <expressão original>
#   Status: true | false
#   Stack: [
#       [estado1], [estado2], ..., [estado5],
#       [estado6], ...
#   ]
#
# POR QUE `per_line = 5`:
#   Limita a 5 estados por linha no arquivo de saída. Sem isso, todas as dezenas
#   de estados ficariam em uma única linha quilométrica, impossível de ler.
#   O valor 5 replica exatamente o formato do exemplo do enunciado.
#
# COMO FUNCIONA:
#   - Cria as linhas de cabeçalho (Input e Status).
#   - Divide `states` em grupos de 5 com list comprehension + fatiamento.
#   - Para cada grupo, gera uma linha indentada com 4 espaços.
#   - Une tudo com '\n' e retorna a string completa do bloco.
def format_output(expr, valid, states):
    lines = [f"Input: {expr}", f"Status: {'true' if valid else 'false'}", "Stack: ["]
    per_line = 5
    # `range(0, len(states), per_line)` gera os índices 0, 5, 10, 15, ...
    # `states[i:i+per_line]` fatia a lista em pedaços de até 5 elementos.
    chunks = [states[i:i + per_line] for i in range(0, len(states), per_line)]
    for chunk in chunks:
        # `", ".join(chunk)` une os estados do grupo com vírgula e espaço.
        lines.append("    " + ", ".join(chunk))
    lines.append("]")
    return "\n".join(lines)


# =====================================================================================
#  FUNÇÃO PRINCIPAL — main()
# =====================================================================================
# RESPONSABILIDADE: Orquestrar o pipeline completo:
#   1. Garantir que o arquivo de entrada existe (criando um de exemplo se necessário).
#   2. Ler todas as expressões do arquivo de entrada.
#   3. Para cada expressão: tokenizar → analisar → formatar o resultado.
#   4. Exibir os resultados no terminal e gravá-los no arquivo de saída.
def main():
    input_file  = "entrada.txt"
    output_file = "saida.txt"

    # Se o arquivo de entrada não existir, criamos um automaticamente com 5 expressões
    # de exemplo — 4 válidas e 1 inválida ("id++id") — para facilitar os testes.
    # `os.path.exists` retorna True se o caminho existe no sistema de arquivos.
    if not os.path.exists(input_file):
        with open(input_file, 'w') as f:
            f.write("id*id\nid*id+(id+id)\n(id+id)*(id+id)\nid+id*id\nid++id\n")
        print(f"Arquivo de entrada criado: {input_file}")

    # Leitura do arquivo de entrada linha por linha.
    # `.strip()` remove espaços em branco e '\n' das bordas de cada linha.
    # O `if line.strip()` no final filtra linhas vazias (ex: linha em branco no final do arquivo).
    with open(input_file) as f:
        expressions = [line.strip() for line in f if line.strip()]

    output_blocks = []

    # Pipeline de compilação para cada expressão:
    for expr in expressions:
        tokens         = tokenize(expr)                    # Passo 1 — Análise Léxica
        valid, states  = parse(tokens)                     # Passo 2 — Análise Sintática
        block          = format_output(expr, valid, states)# Passo 3 — Geração do Relatório
        output_blocks.append(block)
        print(block + "\n")  # Feedback imediato no terminal durante a execução.

    # Grava todos os blocos no arquivo de saída, separados por uma linha em branco.
    # `"\n\n".join(output_blocks)` insere duas quebras de linha entre cada bloco.
    with open(output_file, 'w') as f:
        f.write("\n\n".join(output_blocks) + "\n")
    print(f"Saída gravada em: {output_file}")


# =====================================================================================
#  PONTO DE ENTRADA
# =====================================================================================
# `if __name__ == "__main__"` é uma convenção Python que garante que `main()` só
# seja chamada quando este arquivo for executado DIRETAMENTE (ex: python top_down_parser.py).
# Se outro script importar este arquivo (ex: import top_down_parser), `main()` NÃO
# será chamada automaticamente — apenas as definições de funções e o dicionário
# serão carregados, sem efeitos colaterais indesejados.
if __name__ == "__main__":
    main()
