
import json

def find_notch_1(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    packets = data['data']
    
    for offset in range(43):
        key = f'offset_{offset}'
        matches = [i for i, p in enumerate(packets) if p['channels'].get(key) == 129]
        if matches:
            print(f"Channel {key} has 129 in {len(matches)} packets. First matches: {matches[:10]}")

if __name__ == "__main__":
    find_notch_1('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json')
