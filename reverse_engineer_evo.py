
import binascii

input_path = 'C:/Users/nayla/gravity/Painel-Rot/02250421.dat'

try:
    with open(input_path, 'rb') as f:
        data = f.read()

    print(f"Analisando arquivo Evo: {len(data)} bytes")

    # Tenta detectar a largura do pacote testando várias possibilidades
    # Procuramos a largura que maximiza a consistência dos dados
    best_size = 0
    max_consistency = 0

    for size in range(20, 100):
        consistent_columns = 0
        # Pega uma amostra de 100 pacotes
        num_test = min(100, len(data) // size - 1)
        if num_test < 10: continue
        
        for col in range(size):
            values = [data[i*size + col] for i in range(num_test)]
            # Se a variação for pequena ou nula, é um campo estrutural
            diffs = sum(1 for j in range(len(values)-1) if abs(values[j] - values[j+1]) < 10)
            if diffs > num_test * 0.8:
                consistent_columns += 1
        
        if consistent_columns > max_consistency:
            max_consistency = consistent_columns
            best_size = size

    print(f"\n[DESCOBERTA] Tamanho provável do pacote Evo: {best_size} bytes")

    # Mostra os primeiros 5 pacotes nesse tamanho para inspeção
    if best_size > 0:
        print(f"\nPrimeiros 5 pacotes (Tamanho {best_size}):")
        for i in range(5):
            packet = data[i*best_size : (i+1)*best_size]
            print(f"P{i}: {packet.hex(' ')}")

except Exception as e:
    print(f"Erro na análise: {e}")
