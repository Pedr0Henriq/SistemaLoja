from enum import Enum

class Unidades(Enum):
    m = "metro(s)"
    c = "centímetros"
    u = "unidade(s)"

    @classmethod
    def choices(cls):
        return [(attr.value, attr.name) for attr in cls]
    
    @classmethod
    def is_valid(cls, value):
        return value.lower() in [unit.name for unit in cls]