
import json

def find_max_flow(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    packets = data['data']
    max_f = -1
    max_idx = -1
    
    for i, p in enumerate(packets):
        c = p['channels']
        f_val = (c.get('offset_1', 128) - 128) * 256 + (c.get('offset_2', 128) - 128)
        if f_val > max_f:
            max_f = f_val
            max_idx = i
            
    print(f"Max Flow: {max_f} at index {max_idx}")
    
    # Print context around max flow
    for i in range(max(0, max_idx - 5), min(len(packets), max_idx + 6)):
        c = packets[i]['channels']
        f_val = (c.get('offset_1', 128) - 128) * 256 + (c.get('offset_2', 128) - 128)
        s_val = c.get('offset_4', 128) - 128
        print(f"Index {i:4} | Flow: {f_val:5} | Speed: {s_val:4}")

if __name__ == "__main__":
    find_max_flow('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json')
