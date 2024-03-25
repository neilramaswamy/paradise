import unittest
from dataclasses import dataclass, field

from paradise.engine import ExecutionEngine
from paradise.specification import BaseSpecification, SingleVoteInRing


class SingleVoteMinIdRingElection(BaseSpecification):
    """
    SingleVoteMinIdRingElection is a horrible implementation of ring leader election.

    The protocol is as follows:
        1. When nodes are initialized, they send a Petition to their right neighbor
        2. If a node receives a petition with an ID _less_ than theirs, they respond with a True vote.
        3. If a node receives a True vote, they declare themselves to be leader.

    Clearly, this will fail in a ring where there exist two pairs of nodes (a -> b) and (c -> d) such
    that a < b and c < d.
    """

    ##############
    ## MESSAGES ##
    ##############

    @dataclass
    class Petition(BaseSpecification.Message):
        pass

    @dataclass
    class Vote(BaseSpecification.Message):
        accepted: bool = False

    # User-defined instance variables
    id: int = -1
    is_leader: bool = False

    def __init__(self, id: int, right: int):
        super()

        self.id = id
        self.is_leader = False

        self.send(self.Petition(sender_id=id, recipient_id=right))

    ##############
    ## HANDLERS ##
    ##############

    # "other" is just a POC for now that we can pass arguments to Handlers
    def HandleVote(self, vote: Vote, other: any):
        if vote.accepted:
            self.is_leader = True

    def HandlePetition(self, petition: Petition):
        assert self.id == petition.recipient_id

        vote = self.Vote(self.id, petition.sender_id, False)

        if self.is_leader:
            self.send(vote)
            return

        # Reject senders with higher IDs; lowest ID wins
        if petition.sender_id >= self.id:
            self.send(vote)
        else:
            vote.accepted = True
            self.send(vote)


class BadConsensusTest(unittest.TestCase):
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

        self.assertTrue(voting_protocol.node_map[0].is_leader)
        self.assertTrue(voting_protocol.node_map[1].is_leader)
        self.assertFalse(voting_protocol.node_map[2].is_leader)

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
