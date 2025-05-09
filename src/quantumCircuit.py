import re

def is_unique(lst: list) -> bool:
    return len(lst) == len(set(lst))

class QuantumCircuit:
    def __init__(self):
        self.n_qubits: int = 0
        self.gates: list = []

    def request_qubit(self) -> int:
        self.n_qubits += 1
        return self.n_qubits - 1

    def request_qubits(self, n: int) -> list[int]:
        return [self.request_qubit() for _ in range(n)]

    def add_toffoli(
        self, c1: int, c2: int, target: int, p1: bool = False, p2: bool = False, clean: bool = False,
    ) -> None:
        assert is_unique([c1, c2, target]), f"Control and target qubits must be unique, got {c1}, {c2}, {target}"
        if p1: self.add_x(c1)
        if p2: self.add_x(c2)
        if clean:
            self.add_h(target)
            self.add_t(target)
            self.add_cnot(c1, target)
            self.add_cnot(c2, target)
            self.add_cnot(target, c2)
            self.add_cnot(target, c1)
            self.add_tdg(c1)
            self.add_tdg(c2)
            self.add_t(target)
            self.add_cnot(target, c1)
            self.add_cnot(target, c2)
            self.add_h(target)
            self.add_s(c1)        
        else: self.gates.append({"name": "Tof", "ctrl1": c1, "ctrl2": c2, "target": target})
        if p1: self.add_x(c1)
        if p2: self.add_x(c2)
        
    def add_mcx(
        self, cs: list[int], target: int, ps: list[bool] = [], clean: bool = False,
    ) -> None:
        assert len(cs) <= 2, f"MCX only supports 1 or 2 control qubits, got {len(cs)}"
        if len(cs) == 1:
            self.add_cnot(cs[0], target, ps[0])
        elif len(cs) == 2:
            self.add_toffoli(cs[0], cs[1], target, ps[0], ps[1], clean)
            
    def add_gate(self, gate: dict) -> None:
        self.gates.append(gate.copy())

    def add_cnot(self, ctrl: int, target: int, p: bool = False) -> None:
        if p: self.add_x(ctrl)
        self.gates.append({"name": "CNOT", "ctrl": ctrl, "target": target})
        if p: self.add_x(ctrl)
        
    def add_cz(self, ctrl: int, target: int) -> None:
        self.add_h(target)
        self.gates.append({"name": "CNOT", "ctrl": ctrl, "target": target})
        self.add_h(target)
    
    def add_z(self, target: int) -> None:
        self.add_h(target)
        self.gates.append({"name": "X", "target": target})
        self.add_h(target)

    def add_x(self, target: int) -> None:
        self.gates.append({"name": "X", "target": target})
        
    def add_h(self, target: int) -> None:
        self.gates.append({"name": "HAD", "target": target})
        
    def add_s(self, target: int) -> None:
        self.gates.append({"name": "S", "target": target})
        
    def add_t(self, target: int) -> None:
        self.gates.append({"name": "T", "target": target})
        
    def add_tdg(self, target: int) -> None:
        self.gates.append({"name": "Tdg", "target": target})
        
    @staticmethod
    def deps_of(gate: dict) -> set[int]:
        deps: set[int] = set()
        if gate["name"] == "CNOT":
            deps.add(gate["ctrl"])
            deps.add(gate["target"])
        elif gate["name"] == "Tof":
            deps.add(gate["ctrl1"])
            deps.add(gate["ctrl2"])
            deps.add(gate["target"])
        else:
            deps.add(gate["target"])
        return deps
        
    def to_json(self) -> dict:
        return self.gates

    def to_qasm(self, **kwargs) -> str:
        run_zx: bool = kwargs.get("run_zx", False)
        
        qasm_str: str = "OPENQASM 2.0;\n"
        qasm_str += f'include "qelib1.inc";\n'
        qasm_str += f"qreg q[{self.n_qubits}];\n"
        for gate in self.gates:
            if gate["name"] == "Tof":
                qasm_str += f"ccx q[{gate['ctrl1']}], q[{gate['ctrl2']}], q[{gate['target']}];\n"
            elif gate["name"] == "CNOT":
                qasm_str += f"cx q[{gate['ctrl']}], q[{gate['target']}];\n"
            elif gate["name"] == "X":
                qasm_str += f"x q[{gate['target']}];\n"
            elif gate["name"] == "HAD":
                qasm_str += f"h q[{gate['target']}];\n"
            elif gate["name"] == "S":
                qasm_str += f"s q[{gate['target']}];\n"
            elif gate["name"] == "T":
                qasm_str += f"t q[{gate['target']}];\n"
            elif gate["name"] == "Tdg":
                qasm_str += f"tdg q[{gate['target']}];\n"
            else:
                raise NotImplementedError(f"Unsupported gate: {gate['name']}")
        
        if run_zx:
            import pyzx as zx
            circuit = zx.Circuit.from_qasm(qasm_str)
            graph = circuit.to_graph()
            zx.simplify.full_reduce(graph, quiet=True)
            circuit = zx.extract_circuit(graph, up_to_perm=False)
            circuit = circuit.to_basic_gates()
            circuit = circuit.split_phase_gates()
            return circuit.to_qasm()
        return qasm_str
    
    @staticmethod
    def from_qasm(qasm: str) -> 'QuantumCircuit':
        import pyzx as zx
        qc = zx.Circuit.from_qasm(qasm)
        
        circuit = QuantumCircuit()
        circuit.request_qubits(qc.qubits)
        for gate in qc.gates:
            if gate.name == "Tof":
                circuit.add_toffoli(gate.ctrl1, gate.ctrl2, gate.target)
            elif gate.name == "CNOT":
                circuit.add_cnot(gate.control, gate.target)
            elif gate.name == "CZ":
                circuit.add_cz(gate.control, gate.target)
            elif gate.name == "Z":
                circuit.add_z(gate.target)
            elif gate.name == "X":
                circuit.add_x(gate.target)
            elif gate.name == "HAD":
                circuit.add_h(gate.target)
            elif gate.name == "S":
                circuit.add_s(gate.target)
            elif gate.name == "T":
                circuit.add_t(gate.target)
            elif gate.name == "Tdg":
                circuit.add_tdg(gate.target)
            else:
                raise NotImplementedError(f"Unsupported gate: {gate.name}")
        
        return circuit

    @property
    def num_t(self) -> int:
        return sum(1 for gate in self.gates if gate["name"] in ["T", "Tdg"])
    
    @property
    def num_gates(self) -> int:
        return len(self.gates)