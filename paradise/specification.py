from dataclasses import dataclass
from typing import Optional


class BaseSpecification:
    @dataclass
    class Message:
        sender_id: Optional[int]
        recipient_id: Optional[int]

    # This static variable is a bit dangerous:
    #
    # It stores messages across _all_ subclasses of BaseSpecification. So if
    # BaseSpecification is being used by two different subclasses in the same
    # Python process, messages will be mixed up. We can probably solve this by
    # keeping a map from subclass name to list[Message]. But do note, we need
    # to keep the messages list up here, hoisted to the parent, so that we have
    # access to it inside of recv.
    messages: list[Message] = []

    # The only instance variable we need is the id
    id: int = -1

    def __init__(self, id: int):
        self.id = id

    @staticmethod
    def reset():
        BaseSpecification.messages = []

    def send(self, message: Message):
        BaseSpecification.messages.append(message)

    @staticmethod
    def recv(message_type: str, recipient_id: int) -> Optional[Message]:
        """
        Returns the first Message in BaseSpecification.messages of type
        message_name that is being sent to recipient_id. It removes it from
        the messages list.

        This is actually a fairly problematic way to implement receive. Suppose we
        have two nodes A and B that send messages M1 and M2 (in that order),
        and of the same message_name, to C.

        If we then call recv(message_name, C), we will return M1. However, it's
        possible that we want to simulate the interleaving of send(M1) and then
        send(M2), but M2 <- recv and *then* M1 <- recv.

        That's not currently possible with this implementation. To simulate that
        interleaving, we'd likely need to attach unique identifiers to each message,
        and have users specify which one they'd like to handle.
        """
        found_message: Optional[BaseSpecification.Message] = None

        for message in BaseSpecification.messages:
            name = message.__class__.__name__
            if name.endswith(message_type) and message.recipient_id == recipient_id:
                found_message = message
                break

        if found_message is None:
            return None

        BaseSpecification.messages.remove(found_message)
        return found_message
