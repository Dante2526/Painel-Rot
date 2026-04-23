
import json

def find_stationary_periods(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    packets = data['data']
    
    stationary_periods = []
    current_period = None
    
    for i, p in enumerate(packets):
        c = p['channels']
        speed = abs(c.get('offset_4', 128) - 128)
        
        if speed <= 2:
            if current_period is None:
                current_period = {'start': i, 'end': i}
            else:
                current_period['end'] = i
        else:
            if current_period:
                stationary_periods.append(current_period)
                current_period = None
    
    if current_period:
        stationary_periods.append(current_period)
        
    print(f"{'Start':6} | {'End':6} | {'Dur':6} | {'Avg Flow':10} | {'Avg EG':10} | {'Avg BC':10}")
    print("-" * 60)
    
    for period in stationary_periods:
        start = period['start']
        end = period['end']
        duration = end - start + 1
        
        if duration < 10: continue
        
        flows = []
        egs = []
        bcs = []
        
        for i in range(start, end + 1):
            c = packets[i]['channels']
            f_val = (c.get('offset_1', 128) - 128) * 256 + (c.get('offset_2', 128) - 128)
            eg_val = c.get('offset_11', 128) - 128
            bc_val = c.get('offset_7', 128) - 128
            flows.append(f_val)
            egs.append(eg_val)
            bcs.append(bc_val)
            
        avg_flow = sum(flows) / len(flows)
        avg_eg = sum(egs) / len(egs)
        avg_bc = sum(bcs) / len(bcs)
        
        print(f"{start:6} | {end:6} | {duration:6} | {avg_flow:10.2f} | {avg_eg:10.2f} | {avg_bc:10.2f}")

if __name__ == "__main__":
    find_stationary_periods('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json')
