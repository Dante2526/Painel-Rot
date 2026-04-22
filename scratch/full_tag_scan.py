
import os

def full_scan():
    files = [
        r'C:/Users/nayla/gravity/Painel-Rot/02250421.dat',
        r'C:/Users/nayla/gravity/Painel-Rot/02230812.dat'
    ]

    tags = {
        'EG (&BA)': b'\x26\x82\x80',
        'BC (ДиК)': b'\x84\xe8\x8a',
        'NOTCH (C2)': b'\xc2',
        'HORN (БВ)': b'\xc1\xc2',
        'BELL (БД)': b'\xc1\xc4',
        'HORN+BELL (БЖ)': b'\xc1\xc6',
        'FWD (мДААА)': b'\xcc\xc4\xc0\xc0\xc0',
        'REV (мДААР)': b'\xcc\xc4\xc0\xc0\xd0',
        'PCS (ДиКЯЁ)': b'\xd0\xb8\x4a\x20\x2d\x20\x32\x30\x30\x39' # Tentativa aproximada para PCS
    }

    for path in files:
        if not os.path.exists(path):
            continue
        
        print(f"\n--- Analisando: {os.path.basename(path)} ---")
        with open(path, 'rb') as f:
            data = f.read()
        
        for name, seq in tags.items():
            count = data.count(seq)
            if count > 0:
                first = data.find(seq)
                print(f"  [OK] {name}: {count} ocorrencias (Primeira em {first})")
            else:
                print(f"  [MISS] {name}: Nao encontrado")

if __name__ == "__main__":
    full_scan()
