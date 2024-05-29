class Epr():
    def __init__(self,  epr_id: int, qubits: list, initial_fidelity: float = 1.0) -> None:
        self._epr_id = epr_id
        self._initial_fidelity = initial_fidelity
        self._current_fidelity = initial_fidelity
        # Ainda vamos ver se isso vai ser necessário
        # self.qubits = qubits

    def __str__(self):
        return f'EPR({self.qubits})'
    
    @property
    def epr_id(self):
        return self._epr_id
    
    def get_initial_fidelity(self):
        return self._initial_fidelity
    
    def get_current_fidelity(self):
        return self._current_fidelity