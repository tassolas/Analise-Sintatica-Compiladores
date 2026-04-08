import re
import os

linguagem = {
    "terminal": ['+', '*', '(', ')', 'id', '$'],
    "nonterminal": ['E', 'X', 'T', 'Y', 'F'],
    "gramar": {
        "E": ['TX'],
        "X": ['+TX', 'null'],
        "T": ['FY'],
        "Y": ['*FY', 'null'],
        "F": ['(E)', 'id']
    },
    "first": {
        "E": ['(', 'id'], "X": ['+', 'null'], "T": ['(', 'id'],
        "Y": ['*', 'null'], "F": ['(', 'id']
    },
    "follow": {
        "E": [')', '$'], "X": [')', '$'], "T": ['+', ')', '$'],
        "Y": ['+', ')', '$'], "F": ['*', '+', ')', '$']
    },
    "tableM": {
        "E": {'id': 'TX',   '(':  'TX'},
        "X": {'+':  '+TX',  ')':  'null', '$': 'null'},
        "T": {'id': 'FY',   '(':  'FY'},
        "Y": {'+':  'null', '*':  '*FY', ')': 'null', '$': 'null'},
        "F": {'id': 'id',   '(':  '(E)'}
    }
}


def tokenize(line):
    tokens = []
    for match in re.finditer(r'\+|\*|\(|\)|\w+', line):
        tok = match.group()
        tokens.append('id' if tok.isalnum() or '_' in tok else tok)
    tokens.append('$')
    return tokens


def split_production(prod):
    return re.findall(r'id|[+*()\w]', prod)


def fmt(stack):
    visible = [s for s in stack if s != '$']
    return '[' + ', '.join(visible) + ']'


def parse(tokens):
    table  = linguagem["tableM"]
    terms  = linguagem["terminal"]
    nterms = linguagem["nonterminal"]

    stack  = ['$', 'E']
    states = [fmt(stack)]
    ptr    = 0
    valid  = True

    while True:
        if not stack:
            valid = False
            break

        top = stack[-1]

        if top == '$' and tokens[ptr] == '$':
            if fmt(stack) != '[]':
                stack.pop()
                states.append(fmt(stack))
            break

        token = tokens[ptr]

        if top in terms:
            if top == token:
                stack.pop()
                ptr += 1
                states.append(fmt(stack))
            else:
                valid = False
                stack.pop()
                states.append(fmt(stack))

        elif top in nterms:
            row = table.get(top, {})
            if token not in row:
                valid = False
                stack.pop()
                states.append(fmt(stack))
            else:
                production = row[token]
                stack.pop()

                if production == 'null':
                    stack.append('null')
                    states.append(fmt(stack))
                    stack.pop()
                    states.append(fmt(stack))
                else:
                    for sym in reversed(split_production(production)):
                        stack.append(sym)
                    states.append(fmt(stack))

        else:
            valid = False
            stack.pop()
            states.append(fmt(stack))

    return valid, states


def format_output(expr, valid, states):
    lines = [f"Input: {expr}", f"Status: {'true' if valid else 'false'}", "Stack: ["]
    per_line = 5
    chunks = [states[i:i + per_line] for i in range(0, len(states), per_line)]
    for chunk in chunks:
        lines.append("    " + ", ".join(chunk))
    lines.append("]")
    return "\n".join(lines)


def main():
    input_file  = "entrada.txt"
    output_file = "saida.txt"

    if not os.path.exists(input_file):
        with open(input_file, 'w') as f:
            f.write("id*id\nid*id+(id+id)\n(id+id)*(id+id)\nid+id*id\nid++id\n")
        print(f"Arquivo de entrada criado: {input_file}")

    with open(input_file) as f:
        expressions = [line.strip() for line in f if line.strip()]

    output_blocks = []
    for expr in expressions:
        tokens         = tokenize(expr)
        valid, states  = parse(tokens)
        block          = format_output(expr, valid, states)
        output_blocks.append(block)
        print(block + "\n")

    with open(output_file, 'w') as f:
        f.write("\n\n".join(output_blocks) + "\n")
    print(f"Saída gravada em: {output_file}")


if __name__ == "__main__":
    main()
