from dataclasses import dataclass
from paradise.specification import BaseSpecification
from paradise.engine import ExecutionEngine


class BadConsensus(BaseSpecification):
    ##############
    ## MESSAGES ##
    ##############
    @dataclass
    class Petition(BaseSpecification.Message):
        pass

    @dataclass
    class Vote(BaseSpecification.Message):
        accepted: bool

    # User-defined instance variables
    id: int = -1
    is_leader: bool = False

    def __init__(self, id: int):
        self.id = id
        self.is_leader = False

        self.send(self.Petition(sender_id=id, recipient_id=((id + 1) % 3)))

    ##############
    ## HANDLERS ##
    ##############

    def HandleVote(self, vote: Vote):
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


if __name__ == "__main__":
    nodes = [BadConsensus(0), BadConsensus(1), BadConsensus(2)]

    actions = [
        # Probably can do HandlePetition(_, a, b, c) for additional params,
        # where _ has a special meaning of the actual Message
        "1: HandlePetition",  # Handles petition from 0; 0 <- Vote(true)
        "0: HandleVote",  # 0 handles Vote(true), becomes leader
        "2: HandlePetition",  # Handles petition from 1; 1 <- Vote(true)
        "1: HandleVote",  # 1 handles Vote(true), becomes leader
    ]

    ExecutionEngine.evaluate(nodes, actions)
    [print(node.is_leader) for node in nodes]
