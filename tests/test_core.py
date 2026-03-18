"""Tests for Burnoutradar."""
from src.core import Burnoutradar
def test_init(): assert Burnoutradar().get_stats()["ops"] == 0
def test_op(): c = Burnoutradar(); c.detect(x=1); assert c.get_stats()["ops"] == 1
def test_multi(): c = Burnoutradar(); [c.detect() for _ in range(5)]; assert c.get_stats()["ops"] == 5
def test_reset(): c = Burnoutradar(); c.detect(); c.reset(); assert c.get_stats()["ops"] == 0
def test_service_name(): c = Burnoutradar(); r = c.detect(); assert r["service"] == "burnoutradar"
