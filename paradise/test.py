import unittest
from dataclasses import dataclass

from paradise.engine import ExecutionEngine
from paradise.specification import BaseSpecification


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
    class Petition(BaseSpecification.Message): ...

    @dataclass
    class Vote(BaseSpecification.Message):
        accepted: bool

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
        BaseSpecification.reset()

        nodes = [
            SingleVoteMinIdRingElection(0, right=1),
            SingleVoteMinIdRingElection(1, right=2),
            SingleVoteMinIdRingElection(2, right=0),
        ]

        actions = [
            "HandlePetition(1, _)",
            'HandleVote(0, _, "foo")',
            "HandlePetition(2, _)",
            "HandleVote(1, _, 3)",
        ]

        ExecutionEngine.evaluate(nodes, actions)

        self.assertTrue(nodes[0].is_leader)
        self.assertTrue(nodes[1].is_leader)
        self.assertTrue(not nodes[2].is_leader)

    def test_one_leader(self):
        BaseSpecification.reset()

        zero = SingleVoteMinIdRingElection(0, right=2)
        one = SingleVoteMinIdRingElection(1, right=0)
        two = SingleVoteMinIdRingElection(2, right=1)

        nodes = [zero, one, two]

        actions = [
            "HandlePetition(1, _)",  # 2 -> 1, 1 rejects it
            "HandlePetition(0, _)",  # 1 -> 0, 0 rejects it
            "HandlePetition(2, _)",  # 0 -> 2, 2 accepts it
            'HandleVote(0, _, "p")',
            'HandleVote(1, _, "o")',
            'HandleVote(2, _, "c")',
        ]

        ExecutionEngine.evaluate(nodes, actions)

        self.assertTrue(zero.is_leader)
        self.assertTrue(not one.is_leader)
        self.assertTrue(not two.is_leader)


if __name__ == "__main__":
    unittest.main()
