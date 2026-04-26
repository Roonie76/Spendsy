import os
import logging
from config import settings

logger = logging.getLogger(__name__)

try:
    from agentlightning import LightningStore, LightningTracer
    HAS_LIGHTNING = True
except ImportError:
    HAS_LIGHTNING = False

# Global instances
lightning_store = None
tracer = None

def init_lightning():
    global lightning_store, tracer
    if HAS_LIGHTNING:
        traces_dir = os.path.join(os.path.dirname(__file__), "traces")
        os.makedirs(traces_dir, exist_ok=True)
        lightning_store = LightningStore(traces_dir=traces_dir)
        tracer = LightningTracer(store=lightning_store)
        logger.info(f"Agent Lightning initialized. Traces stored in {traces_dir}")
    else:
        logger.warning("Agent Lightning not found. Tracing disabled.")

# Call initialization
init_lightning()

def get_tracer():
    return tracer

def get_store():
    return lightning_store
