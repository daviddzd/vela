"""Run one replication (used by the experiment pool and by the tests)."""
from simulation.sirag.data import load_world
from simulation.sirag.metrics import summarize
from simulation.sirag.model import Model, Params


def run_one(params: Params) -> dict:
    model = Model(load_world(params.labor_rules), params)
    requests = model.run()
    return summarize(model, requests)
