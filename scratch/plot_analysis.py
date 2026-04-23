
import json
import matplotlib.pyplot as plt

def plot_telemetry(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    packets = data['data']
    
    flow = []
    speed = []
    eg = []
    er = []
    bc = []
    
    for p in packets:
        c = p['channels']
        # Flow = (offset_1 - 128) * 256 + (offset_2 - 128)
        f_val = (c.get('offset_1', 128) - 128) * 256 + (c.get('offset_2', 128) - 128)
        flow.append(f_val)
        
        # Speed = offset_4 - 128
        s_val = c.get('offset_4', 128) - 128
        speed.append(s_val)
        
        # EG = offset_11 - 128
        eg_val = c.get('offset_11', 128) - 128
        eg.append(eg_val)
        
        # ER = offset_3 - 128
        er_val = c.get('offset_3', 128) - 128
        er.append(er_val)
        
        # BC = offset_7 - 128
        bc_val = c.get('offset_7', 128) - 128
        bc.append(bc_val)

    plt.figure(figsize=(12, 10))
    
    plt.subplot(3, 1, 1)
    plt.plot(flow, label='Fluxo (Ar)')
    plt.title('Fluxo de Abastecimento de Ar')
    plt.ylabel('CFM (Est.)')
    plt.legend()
    
    plt.subplot(3, 1, 2)
    plt.plot(speed, label='Velocidade')
    plt.plot(eg, label='EG (Brake Pipe)')
    plt.plot(er, label='ER (Equalizing)')
    plt.title('Velocidade e Pressões')
    plt.ylabel('PSI / km/h')
    plt.legend()
    
    plt.subplot(3, 1, 3)
    plt.plot(bc, label='BC (Independente)')
    plt.title('Freio Independente')
    plt.ylabel('PSI')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('c:/Users/nayla/.antigravity/Painel-Rot/scratch/analysis_plot.png')
    print("Plot saved to scratch/analysis_plot.png")

if __name__ == "__main__":
    plot_telemetry('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json')
