import unittest
from random import Random

from simulation.src.model import Gateway, is_connected, run_trial, simulate


class ConnectivityTests(unittest.TestCase):
    def setUp(self):
        self.networks = ["A", "B", "C"]

    def test_path_is_connected(self):
        gateways = [
            Gateway("ab", "A", "B", "op1"),
            Gateway("bc", "B", "C", "op2"),
        ]
        self.assertTrue(is_connected(self.networks, gateways))

    def test_missing_bridge_disconnects(self):
        gateways = [Gateway("ab", "A", "B", "op1")]
        self.assertFalse(is_connected(self.networks, gateways))

    def test_alternative_path_survives_single_edge_failure(self):
        gateways = [
            Gateway("ab", "A", "B", "op1"),
            Gateway("bc", "B", "C", "op2"),
            Gateway("ac", "A", "C", "op3"),
        ]
        self.assertTrue(is_connected(self.networks, gateways, {"ab"}))

    def test_same_network_is_connected(self):
        self.assertTrue(is_connected(["A"], [], source="A", target="A"))

    def test_unknown_endpoint_raises(self):
        with self.assertRaises(ValueError):
            is_connected(["A", "B"], [], source="X", target="B")

    def test_zero_failures_produce_full_availability(self):
        gateways = [Gateway("ab", "A", "B", "op1")]
        result = simulate(["A", "B"], gateways, trials=50,
                          gateway_failure_probability=0,
                          operator_failure_probability=0)
        self.assertEqual(result["availability"], 1.0)

    def test_certain_gateway_failure_produces_zero_availability(self):
        gateways = [Gateway("ab", "A", "B", "op1")]
        result = simulate(["A", "B"], gateways, trials=50,
                          gateway_failure_probability=1,
                          operator_failure_probability=0)
        self.assertEqual(result["availability"], 0.0)

    def test_shared_operator_failure_disables_all_its_gateways(self):
        gateways = [
            Gateway("ab1", "A", "B", "same"),
            Gateway("ab2", "A", "B", "same"),
        ]
        outcome = run_trial(["A", "B"], gateways, 0, 1, Random(1))
        self.assertFalse(outcome.connected)
        self.assertEqual(outcome.active_gateways, 0)

    def test_invalid_probability_raises(self):
        with self.assertRaises(ValueError):
            simulate(["A", "B"], [Gateway("g", "A", "B", "op")],
                     gateway_failure_probability=1.5)


if __name__ == "__main__":
    unittest.main()
