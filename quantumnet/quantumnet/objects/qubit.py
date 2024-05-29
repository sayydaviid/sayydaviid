class Qubit():
    def __init__(self, qubit_id: int, initial_fidelity: float = 1.0) -> None:
        self.qubit_id = qubit_id
        self._qubit_state = None
        self._initial_fidelity = initial_fidelity
        self._current_fidelity = initial_fidelity

    def __str__(self):
        return f"Qubit {self.qubit_id} with state {self._qubit_state}"

    def get_initial_fidelity(self):
        return self._initial_fidelity
    
    def get_current_fidelity(self):
        return self._current_fidelity
    