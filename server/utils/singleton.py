from __future__ import annotations

from abc import ABCMeta
from typing import Any, Dict


class SingletonMeta(type):
    """
    Meta-classe para classes que seguem o padrão Singleton.
    """

    _instances: Dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(metaclass=SingletonMeta):
    """
    Classe base para implementar o padrão Singleton.
    """

    pass


class AbstractSingletonMeta(ABCMeta, SingletonMeta):
    """
    Mixin para poder implementar Singletons abstratos.
    """

    pass


class AbstractSingleton(metaclass=AbstractSingletonMeta):
    """
    Classe base para Singletons abstratos.
    """

    pass
