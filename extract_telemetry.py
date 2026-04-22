
import json

def extract_from_blocks(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    # Procura pelo bloco que começa com 03 90 a0 (que parece conter EG)
    # ou simplesmente divide o arquivo em blocos de 43 bytes e procura por sub-blocos.
    # Mas o dump_43 mostrou que os blocos de 26 bytes não estão em offsets fixos.
    
    # Vamos procurar a sequência '03 90 a0' como marcador de início de telemetria
    marker = b'\x03\x90\xa0'
    indices = [i for i in range(len(data)) if data.startswith(marker, i)]
    
    telemetry = []
    for idx in indices:
        # Pega 26 bytes a partir do 03
        block = data[idx : idx + 26]
        if len(block) < 26: continue
        
        # Canais candidatos
        entry = {
            "time": idx, # Usar offset como tempo por enquanto
            "c1": block[1],  # 0x90 ?
            "c2": block[7],  # 0x90 ?
            "c3": block[16], # 0x90 ?
            "c4": block[22], # 0x87 ?
        }
        telemetry.append(entry)
    
    with open('telemetry.json', 'w') as f:
        json.dump(telemetry, f)
    print(f"Extracted {len(telemetry)} points to telemetry.json")

if __name__ == "__main__":
    extract_from_blocks('02230812.dat')
