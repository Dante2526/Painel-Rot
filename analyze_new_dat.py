import sys

def analyze_dat(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    valid_markers = [0x01, 0x03]
    valid_magics = [0x81, 0x88, 0x89, 0x85, 0x90, 0x99]
    
    packets = []
    i = 0
    while i < len(data) - 26:
        marker = data[i]
        magic = data[i+3]
        
        if marker in valid_markers and magic in valid_magics:
            packet = data[i:i+26]
            packets.append(packet)
            i += 26
        else:
            i += 1
            
    print(f"Total packets found: {len(packets)}")
    
    if not packets:
        return
        
    # Analyze some offsets
    # offset_11: EG, offset_3: ER, offset_4: Speed, offset_15: Amps
    offsets_to_check = [3, 4, 7, 11, 14, 15, 21, 22]
    
    stats = {offset: [] for offset in offsets_to_check}
    
    for p in packets:
        for offset in offsets_to_check:
            stats[offset].append(p[offset])
            
    for offset in offsets_to_check:
        vals = stats[offset]
        min_val = min(vals)
        max_val = max(vals)
        avg_val = sum(vals) / len(vals)
        # Unique values (first 10)
        unique_vals = sorted(list(set(vals)))
        print(f"Offset {offset:2}: Min={min_val:3}, Max={max_val:3}, Avg={avg_val:6.2f}, Unique count={len(unique_vals)}")
        if len(unique_vals) < 20:
            print(f"  Unique values: {unique_vals}")
        else:
            print(f"  First 10 unique values: {unique_vals[:10]}")

if __name__ == '__main__':
    analyze_dat('C:/Users/nayla/gravity/Painel-Rot/02250421.dat')
