
import json

def find_trend(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    packets = data['data']
    
    for offset in range(43):
        key = f'offset_{offset}'
        values = [p['channels'].get(key, 128) for p in packets]
        
        # Check first 50 vs last 50
        start_avg = sum(values[:50]) / 50
        end_avg = sum(values[-50:]) / 50
        diff = start_avg - end_avg
        
        if abs(diff) > 10:
            print(f"Channel {key:10} | Start: {start_avg:6.2f} | End: {end_avg:6.2f} | Diff: {diff:6.2f}")

if __name__ == "__main__":
    find_trend('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json')
