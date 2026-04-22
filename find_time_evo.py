
import binascii

input_path = 'C:/Users/nayla/gravity/Painel-Rot/02250421.dat'

try:
    with open(input_path, 'rb') as f:
        data = f.read()

    print(f"Buscando padrões de tempo em {len(data)} bytes...")

    # Procura por sequências de bytes que aumentam de 1 em 1
    # Ex: [..., X, ..., X+1, ..., X+2]
    # Isso geralmente indica o contador de segundos
    for offset in range(50):
        found = []
        last_val = -1
        for i in range(offset, min(2000, len(data)), 26): # Testa 26 primeiro
            val = data[i]
            if last_val != -1 and val == (last_val + 1) % 256:
                found.append(i)
            last_val = val
        
        if len(found) > 10:
            print(f"[PADRÃO ENCONTRADO] Possível contador no offset {offset} com passo 26")

    # Procura especificamente pelo marcador 0x01 ou 0x03 e mostra o contexto
    print("\nLocalizando Marcadores 0x01/0x03:")
    indices = [i for i, x in enumerate(data) if x in [0x01, 0x03]]
    for idx in indices[:10]:
        ctx = data[idx:idx+10].hex(' ')
        print(f"Index {idx}: {ctx}")

except Exception as e:
    print(f"Erro: {e}")
