from enum import Enum

class Unidades(Enum):
    METRO = "m"
    CENTIMETRO = "c"
    UNIDADE = "u"

    @classmethod
    def choices(cls):
        return [(attr.value, attr.name) for attr in cls]
    
    @classmethod
    def is_valid(cls, value):
        return value.lower() in [unit.value for unit in cls]