# models/user.py

class Utente:
    def __init__(self, username, role, password):
        self.username = username
        self.role = role
        self.password = password

utenti = [
    Utente("Alessio", "warehouse", "ciao"),
    Utente("Thomas", "spare_parts", "1234")
]