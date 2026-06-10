import numpy as np
import socket
import json

class UserController:
    def __init__(self, precomputed_file_path=None):
        self.simulationtime = 0.0
        self.PORT = 5005
        
        print("\n" + "="*50)
        print("[TCP Controller] TCP Server Module (Bridge) started!")
        
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('0.0.0.0', self.PORT))
        self.srv.listen(1)
        
        print(f"[TCP Controller] Listening on port {self.PORT}...")
        print("[TCP Controller] ---> PRESS 'RUN' IN SIMULINK NOW! <---")
        
        self.conn, self.addr = self.srv.accept()
        self.conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def step(self, instantaneous_state, Dt):
        self.simulationtime += Dt
        
        # 1. DYNAMIC EXTRACTION AND RADAR
        try:
            arr = np.array(instantaneous_state).flatten()
            y_phys = arr.tolist()
            max_val = np.max(np.abs(arr)) if len(arr) > 0 else 0.0
        except Exception as e:
            y_phys = []
            max_val = 0.0
            
        z_mod = [] # Simulink will pad with zeros if necessary

        if int(self.simulationtime/Dt) % 50 == 0:
            print(f"[Python Radar] t={self.simulationtime:.2f}s | Max Y Value={max_val:.6f}")

        # 2. SEND TO SIMULINK
        resp = json.dumps({'z': z_mod, 'y': y_phys}).encode()
        try:
            self.conn.sendall(len(resp).to_bytes(4, 'big') + resp)
            
            # 3. RECEIVE COMMANDS FROM SIMULINK
            hdr = b''
            while len(hdr) < 4: 
                chunk = self.conn.recv(4 - len(hdr))
                if not chunk: raise ConnectionError("Simulink closed the connection.")
                hdr += chunk
            mlen = int.from_bytes(hdr, 'big')
            
            raw_data = b''
            while len(raw_data) < mlen: 
                chunk = self.conn.recv(mlen - len(raw_data))
                if not chunk: raise ConnectionError("Simulink closed the connection.")
                raw_data += chunk
            data = json.loads(raw_data.decode())
            
            u = data.get('u', []) # Receive generic array of commands
        except Exception as e:
            u = []

        # Convert Simulink array to dictionary F1, F2... Fn
        out_dict = {}
        for i, val in enumerate(u):
            out_dict[f"F{i+1}"] = val
            
        # Fallback for generic controllers (maps to F1, F2... F4, E1, E2 if exactly 6 commands)
        if len(u) == 6:
             out_dict = {"F1":u[0], "F2":u[1], "F3":u[2], "F4":u[3], "E1":u[4], "E2":u[5]}

        return out_dict

    def __del__(self):
        try:
            self.conn.close()
            self.srv.close()
        except:
            pass