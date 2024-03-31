from __future__ import annotations

import dataclasses
import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeAlias, cast


@dataclass
class Edge:
    """
    Edge represents a directed edge between two nodes in the system.

    src_clock and dst_clock are the logical times at which a message is sent and received,
    respectively. These effectively just give us ordering along the time axis, and as long
    as the UI respects that a smaller time is always rendered to the left of a larger time,
    it will display the system state correctly.
    """
    src: str
    src_clock: int

    # The name of the message being sent from src to dst
    message_type: str

    # The node <dst> calls <dst_handler> at logical time <dst_clock>
    dst: str
    dst_handler: str
    dst_clock: int


@dataclass
class Snapshot:
    """
    Snapshot is JSON-serializable system state. It should be possible for a rendering library
    to take a snapshot and render it without needing to "derive" system properties itself.
    """

    # Ordered list of nodes in the system. These should be rendered from top to bottom.
    nodes: list[int]
    edges: list[Edge]


class IntermediateRepresentation:
    # TODO: Update all NodeIds to be stringifiable
    def __init__(self, nodes: list[int]):
        self.__nodes = nodes
        self.__edges: list[Edge] = []

    def receive(
            self,
            im: BaseSpecification.InternalMessage,
            handler_name: str):
        """
        Receive gets called when a recipient node handles a message from a sender
        node. The handler that the recipient node calls is named handle_name.

        """
        assert im.dst_clock is not None

        e = Edge(
            str(im.message.sender_id),
            im.src_clock,

            str(im.message.__class__.__name__),

            str(im.message.recipient_id),
            handler_name,
            cast(int, im.dst_clock)
        )
        
        self.__edges.append(e)
    
    def serialize(self) -> str:
        snapshot = Snapshot(self.__nodes, self.__edges)
        return json.dumps(dataclasses.asdict(snapshot))


class BaseSpecification:
    @dataclass
    class Message:
        sender_id: int
        recipient_id: int
    
    @dataclass
    class InternalMessage:
        message: BaseSpecification.Message

        src_clock: int
        # dst_clock is None because it is not known at sending time when a message will be received
        dst_clock: int | None

    def __init__(self, node_map: dict[int, Any]):
        # Logical clock of the system. Every time that we call send() or act(),
        # we increment the clock.
        self.__clock = 0
        self._ir = IntermediateRepresentation(list(node_map.keys()))

        self.node_map = node_map
        self.__messages: dict[int, list[BaseSpecification.InternalMessage]] = {i: [] for i in node_map}

    def send(self, messages: list[Message]):
        for message in messages:
            recipient_id = message.recipient_id
            internal_message = BaseSpecification.InternalMessage(message, self.__clock, None)

            self.__messages[recipient_id].append(internal_message)

    def initialize(self, node_id: int):
        self.send(self.node_map[node_id].initialize())

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
        
        handler: Callable[[BaseSpecification.Message], list[BaseSpecification.Message]] = getattr(node, handler_name)
        found_im: BaseSpecification.InternalMessage | None = None

        if preferred_message is not None:
            for im in self.__messages[node_id]:
                if im.message == preferred_message:
                    found_im = im 
                    break 
            if found_im is None:
                raise Exception("Could not find preferred message")
        else:
            raw_message_name = handler_name.split("_")[1]
            raw_message_type = BaseSpecification.__convert_to_pascal_case(raw_message_name)

            for im in self.__messages[node_id]:
                # Case insensitive in case users do something like "HTTPMessage"
                if im.message.__class__.__name__.lower() == raw_message_type:
                    found_im = im 
                    break
            if found_im is None:
                raise Exception("Could not find message of type " + raw_message_type)

        assert(found_im is not None)
        self.__clock += 1
        found_im.dst_clock = self.__clock

        self._ir.receive(found_im, handler_name)
        self.__messages[node_id].remove(found_im)

        new_messages = handler(found_im.message)
        self.send(new_messages)


    @staticmethod
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
    def __init__(self, nodes: list[int]) -> None:
        node_map: dict[int, _SingleVoteInRingNode] = {}

        for i, n in enumerate(nodes):
            node_map[n] = _SingleVoteInRingNode(n, nodes[(i + 1) % len(nodes)])

        super().__init__(node_map)
    

    @staticmethod
    def CheckMultipleLeaders(test_fn):
        def wrapper(self):
            voting_protocol: SingleVoteInRing = test_fn(self)

            num_leaders = 0
            for node in voting_protocol.node_map.values():
                if node.is_leader:
                    num_leaders += 1
            
            self.assertGreater(num_leaders, 1)
        return wrapper

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
    
    def initialize(self, node_id: int):
        super().initialize(node_id)

    
class _SingleVoteInRingNode():
    Vote: TypeAlias = SingleVoteInRing.Vote
    Petition: TypeAlias = SingleVoteInRing.Petition

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
