
import os

def validate():
    path = r'C:/Users/nayla/gravity/Painel-Rot/02250421.dat'
    if not os.path.exists(path):
        print("Arquivo nao encontrado.")
        return

    with open(path, 'rb') as f:
        data = f.read()

    print(f"Analisando arquivo: {path} ({len(data)} bytes)")

    # 1. EG (&BA) - 26 82 80
    eg_tag = b'\x26\x82\x80'
    indices = [i for i in range(len(data)) if data.startswith(eg_tag, i)]
    print(f"\nEG (&BA) - {len(indices)} ocorrencias")
    if indices:
        for i in indices[:5]:
            val_raw = data[i+3]
            val_psi = val_raw - 64
            print(f"  Pos {i}: {data[i:i+5].hex(' ')} -> Valor: {val_raw} (-64 = {val_psi} PSI)")

    # 2. HORN+BELL (БЖ) - C1 C6
    hb_tag = b'\xc1\xc6'
    hb_indices = [i for i in range(len(data)) if data.startswith(hb_tag, i)]
    print(f"\nHORN+BELL (БЖ) - {len(hb_indices)} ocorrencias")
    if hb_indices:
        for i in hb_indices[:5]:
            print(f"  Pos {i}: {data[i:i+5].hex(' ')}")

    # 3. NOTCH - C2
    notch_tag = b'\xc2'
    # Notch costuma vir depois do label? O usuario disse "NOTCH C2". 
    # E mencionou "BЖ precede o NOTCH В│ (Ponto 3)".
    # Vamos ver o que vem depois de C2.
    n_indices = [i for i in range(len(data)) if data.startswith(notch_tag, i)]
    print(f"\nNOTCH (C2) - {len(n_indices)} ocorrencias")
    if n_indices:
        for i in n_indices[:5]:
            print(f"  Pos {i}: {data[i:i+5].hex(' ')}")

    # 4. Delimitador 0xEB
    eb_count = data.count(b'\xeb')
    print(f"\nDelimitador 0xEB: {eb_count} ocorrencias")

if __name__ == "__main__":
    validate()
