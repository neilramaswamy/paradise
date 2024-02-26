"""

evaluation class should reflect:

- methods that start with Handle* are handlers
- 


"""

from dataclasses import dataclass
from typing import Optional
import inspect


class BaseSpecification:
    # A Message contains the to/from information of a message sent between
    # two nodes. If a subclass of a Message is returned from a Handle* method
    # and the sender_id or recipient_id are None, they are automatically
    # populated.
    @dataclass
    class Message:
        sender_id: Optional[int]
        recipient_id: Optional[int]

    # Static variables
    # This is dangerous; why it is dangerous is left as an exercise to the reader
    messages: list[Message] = []

    def send(self, message: Message):
        BaseSpecification.messages.append(message)

    @staticmethod
    def recv(message_name: str, recipient_id: int) -> Optional[Message]:
        """
        Returns the first Message in BaseSpecification.messages of type
        message_name that is being sent to recipient_id. It removes it from
        the messages list.
        """
        found_message: Optional[BaseSpecification.Message] = None

        for message in BaseSpecification.messages:
            name = message.__class__.__name__
            if name.endswith(message_name) and message.recipient_id == recipient_id:
                found_message = message
                break

        if found_message is None:
            return None

        BaseSpecification.messages.remove(found_message)
        return found_message


# Extend
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
        super()

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


class ExecutionEngine:
    # Retrives all the methods in clazz that start with Handle* and returns a
    # map from that method name to the method
    @staticmethod
    def extract_handlers(clazz) -> dict[str, any]:
        members = clazz.__dict__.keys()
        handlers_only = [member for member in members if member.startswith("Handle")]

        handlers = {}
        for handler_name in handlers_only:
            handlers[handler_name] = clazz.__dict__[handler_name]

        return handlers

    @staticmethod
    def extract_message_from_handler(handler: str) -> str:
        handle_str = "Handle"
        return handler[len(handle_str) :]

    @staticmethod
    def evaluate(nodes: list[BaseSpecification], actions: list[str]):
        handlers = ExecutionEngine.extract_handlers(BadConsensus)

        for action in actions:
            recipient_id = int(action[0])
            assert recipient_id >= 0 and recipient_id < len(nodes)
            target_node = nodes[recipient_id]

            # Something like "HandlePetitiion"
            handler_string = action[action.index("Handle") :]
            handler = handlers[handler_string]

            message_string = ExecutionEngine.extract_message_from_handler(
                handler_string
            )
            message = BaseSpecification.recv(message_string, recipient_id)

            # TODO: If message == None, then we have an invalid specification.

            print(f"For {recipient_id}, evaluating {message} with {handler}")
            handler(target_node, message)


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
