
import json

def analyze_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    packets = data['data']
    num_packets = len(packets)
    print(f"Total packets: {num_packets}")
    
    # Get all channel keys
    channels = packets[0]['channels'].keys()
    
    for channel in channels:
        values = [p['channels'][channel] for p in packets]
        min_v = min(values)
        max_v = max(values)
        avg_v = sum(values) / len(values)
        unique = len(set(values))
        
        if unique < 10:
            print(f"{channel:10} | Min: {min_v:3} | Max: {max_v:3} | Avg: {avg_v:6.2f} | Unique: {unique} | Values: {set(values)}")
        else:
            print(f"{channel:10} | Min: {min_v:3} | Max: {max_v:3} | Avg: {avg_v:6.2f} | Unique: {unique}")

if __name__ == "__main__":
    analyze_json('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json')
