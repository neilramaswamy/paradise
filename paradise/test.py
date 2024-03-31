import unittest
from dataclasses import dataclass, field

from paradise.engine import ExecutionEngine
from paradise.specification import BaseSpecification, SingleVoteInRing


class BadConsensusTest(unittest.TestCase):
    @SingleVoteInRing.CheckMultipleLeaders
    def test_two_leaders(self):
        voting_protocol = SingleVoteInRing([0, 1, 2])

        # Initialize
        voting_protocol.initialize(0)
        voting_protocol.initialize(1)
        voting_protocol.initialize(2)

        voting_protocol.handle_petition(0)
        voting_protocol.handle_vote(2)
        voting_protocol.handle_petition(2) 
        voting_protocol.handle_petition(1) 
        voting_protocol.handle_vote(1)
        voting_protocol.handle_vote(0)

        # TODO: Need to test that _ir.edges is correct
        voting_protocol._ir.serialize()

        return voting_protocol

    def test_one_leader(self):
        voting_protocol = SingleVoteInRing([2, 1, 0])

        voting_protocol.initialize(0)
        voting_protocol.initialize(1)
        voting_protocol.initialize(2)

        voting_protocol.handle_petition(1)
        voting_protocol.handle_petition(0)
        voting_protocol.handle_petition(2)
        voting_protocol.handle_vote(0)
        voting_protocol.handle_vote(1)
        voting_protocol.handle_vote(2)

        self.assertTrue(voting_protocol.node_map[0].is_leader)
        self.assertFalse(voting_protocol.node_map[1].is_leader)
        self.assertFalse(voting_protocol.node_map[2].is_leader)


if __name__ == "__main__":
    unittest.main()
