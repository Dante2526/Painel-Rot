
import collections

input_path = 'C:/Users/nayla/gravity/Painel-Rot/02250421.dat'

try:
    with open(input_path, 'rb') as f:
        data = f.read()

    print(f"Tamanho total do arquivo: {len(data)} bytes")

    # Tenta encontrar a periodicidade (tamanho do pacote)
    # Procuramos por bytes que se repetem a cada N posições
    for size in [26, 32, 43, 64, 128]:
        matches = 0
        for i in range(0, len(data) - size * 2, size):
            if data[i] == data[i + size]:
                matches += 1
        print(f"Testando tamanho {size}: {matches} matches")

    # Dump dos primeiros 200 bytes para inspeção visual detalhada
    print("\nHex Dump (primeiros 200 bytes):")
    hex_str = data[:200].hex(' ')
    rows = [hex_str[i:i+48] for i in range(0, len(hex_str), 48)]
    for row in rows:
        print(row)

except Exception as e:
    print(f"Erro: {e}")
