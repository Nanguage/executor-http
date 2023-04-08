from executor.engine import Engine
from .config import engine_setting


engine = Engine(engine_setting)


def reload_engine():
    global engine
    engine = Engine(engine_setting)
    from .utils import reload_routers
    reload_routers()
