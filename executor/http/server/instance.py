from executor.engine import Engine

engine = Engine()

def reload_engine():
    global engine
    engine = Engine()
    from .utils import reload_routers
    reload_routers()
