
import os

def full_scan():
    files = [
        r'C:/Users/nayla/gravity/Painel-Rot/02250421.dat',
        r'C:/Users/nayla/gravity/Painel-Rot/02230812.dat'
    ]

    tags = {
        'EG': b'\x26\x82\x80',
        'BC': b'\x84\xe8\x8a',
        'NOTCH': b'\xc2',
        'HORN': b'\xc1\xc2',
        'BELL': b'\xc1\xc4',
        'HORN_BELL': b'\xc1\xc6',
        'FWD': b'\xcc\xc4\xc0\xc0\xc0',
        'REV': b'\xcc\xc4\xc0\xc0\xd0',
        'PCS': b'\xd0\xb8\x4a' # Parcial para PCS
    }

    for path in files:
        if not os.path.exists(path):
            continue
        
        print(f"\nFILE: {os.path.basename(path)}")
        with open(path, 'rb') as f:
            data = f.read()
        
        for name, seq in tags.items():
            count = data.count(seq)
            if count > 0:
                first = data.find(seq)
                print(f"  [OK] {name}: {count} found (First at {first})")
            else:
                print(f"  [MISS] {name}: Not found")

if __name__ == "__main__":
    full_scan()
