# models/missing.py

class MissingPart:
    def __init__(self, code, description, quantity, position, order):
        self.code = code
        self.description = description
        self.quantity = quantity
        self.position = position
        self.order = order

table_datas = [
    MissingPart("YY1M0366", "MOTORE UL", "3", "MGVRT", order="25.PER.088"),
    MissingPart("YY1P0188", "BOCCOLA", "78", "AVA", order="25.PER.088"),
    MissingPart("YL000343", "FILTRO ARIA", "32", "E01", order="25.PER.088"),
    MissingPart("YL1E0190", "CAVO ENCODER", "89", "AVA", order="25.PER.088"),
    MissingPart("YPR1E078", "CAVO SEGNALE", "35", "MGVRT", order="25.PER.088"),
    MissingPart("YL000035", "PRESSACAVO IN OTTONE", "3", "AVA", order="25.PER.088"),
    MissingPart("YY1M0240", "MOTORE TRIFASE", "89", "MGVRT", order="25.PER.088"),
]

columns = ['code','description','quantity','position','order']