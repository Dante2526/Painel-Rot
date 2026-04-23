
import json

def analyze_start(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    packets = data['data']
    
    print(f"{'Idx':4} | {'Flow':5} | {'Speed':5} | {'EG':5} | {'BC':5} | {'ER':5} | {'O_15':5}")
    print("-" * 50)
    
    for i in range(130):
        c = packets[i]['channels']
        f_val = (c.get('offset_1', 128) - 128) * 256 + (c.get('offset_2', 128) - 128)
        s_val = c.get('offset_4', 128) - 128
        eg_val = c.get('offset_11', 128) - 128
        bc_val = c.get('offset_7', 128) - 128
        er_val = c.get('offset_3', 128) - 128
        o15_val = c.get('offset_15', 128) - 128
        
        print(f"{i:4} | {f_val:5} | {s_val:5} | {eg_val:5} | {bc_val:5} | {er_val:5} | {o15_val:5}")

if __name__ == "__main__":
    analyze_start('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json')
