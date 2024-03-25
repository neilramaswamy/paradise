from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Callable, Optional


class BaseSpecification:
    @dataclass
    class Message:
        sender_id: int
        recipient_id: int

    def __init__(self, node_map: dict[int, any]):
        self.node_map = node_map
        self.messages: dict[int, list[BaseSpecification.Message]] = {i: [] for i in node_map}

    def send(self, messages: list[Message]):
        for message in messages:
            self.messages[message.recipient_id].append(message)

    def act(self, node_id: int, preferred_message: BaseSpecification.Message | None = None):
        # Callstack magic to figure out the calling method 
        node = self.node_map[node_id]

        stack = traceback.extract_stack()
        handler_name: Optional[str] = None

        for frame in reversed(stack):
            if frame.name.startswith("handle_"):
                handler_name = frame.name
        
        if handler_name is None:
            raise Exception("Could not find calling method")
        
        handler = getattr(node, handler_name)
        found_message: BaseSpecification.Message | None = None

        if preferred_message is not None:
            for message in self.messages[node_id]:
                if message == preferred_message:
                    found_message = message
                    break 
            if found_message is None:
                raise Exception("Could not find preferred message")
        else:

            # God im sorry for what im about to do
            raw_message_name = handler_name.split("_")[1]
            raw_message_type = BaseSpecification.__convert_to_pascal_case(raw_message_name)

            for message in self.messages[node_id]:
                # Case insensitive in case users do something like "HTTPMessage"
                if message.__class__.__name__.lower() == raw_message_type:
                    found_message = message
                    break
            if found_message is None:
                raise Exception("Could not find message of type " + raw_message_type)

        assert(found_message is not None)
        self.messages[node_id].remove(found_message)

        new_messages = handler(found_message)
        self.send(new_messages)


    def __convert_to_pascal_case(snake_str: str):
        if snake_str.startswith('_') or snake_str.endswith('_') or '__' in snake_str:
            raise ValueError("Invalid input string")

        words = snake_str.split('_')
        capitalized_words = [word.lower() for word in words]
        return ''.join(capitalized_words)


class SingleVoteInRing(BaseSpecification):
    """

    The handler methods, named handle_<message_type>, are effectively sugar
    around handling a particular <message_type>. If the specific message is
    not specified, then the engine will pick a message of that type. If the
    specific message is specified, then the engine will try to search for a
    message that deeply equals the specified one.
    """
    def __init__(self, nodes: list[int]) -> SingleVoteInRing:
        node_map: dict[int, _SingleVoteInRingNode] = {}

        for i, n in enumerate(nodes):
            node_map[n] = _SingleVoteInRingNode(n, nodes[(i + 1) % len(nodes)])

        super().__init__(node_map)

    @dataclass
    class Petition(BaseSpecification.Message):
        pass

    @dataclass
    class Vote(BaseSpecification.Message):
        accepted: bool

    def handle_petition(self, node_id: int, petition: Petition | None = None):
        self.act(node_id, petition)
    
    def handle_vote(self, node_id: int, vote: Vote | None = None):
        self.act(node_id, vote)
    
    # Have to explicitly call initialize
    def initialize(self, node_id: int):
        self.send(self.node_map[node_id].initialize())

    
class _SingleVoteInRingNode():
    Vote = SingleVoteInRing.Vote
    Petition = SingleVoteInRing.Petition

    def __init__(self, id: int, right: int):
        self.id = id
        self.is_leader = False
        self.right = right
    
    def __repr__(self):
        return f"Node {self.id} is leader: {self.is_leader}"

    # No arguments given to initialize
    def initialize(self) -> list[BaseSpecification.Message]:
        return [self.Petition(self.id, self.right)]

    def handle_vote(self, vote: Vote) -> list[BaseSpecification.Message]:
        assert self.id == vote.recipient_id
        if vote.accepted:
            self.is_leader = True
        return []

    def handle_petition(self, petition: Petition):
        assert self.id == petition.recipient_id

        # Reject senders with higher IDs; lowest ID wins
        if petition.sender_id >= self.id or self.is_leader:
            return [self.Vote(self.id, petition.sender_id, False)]
        else:
            return [self.Vote(self.id, petition.sender_id, True)]
