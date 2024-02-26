from paradise.specification import BaseSpecification


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
    def evaluate(
        nodes: list[BaseSpecification],
        actions: list[str],
    ):
        assert len(nodes) > 0
        handlers = ExecutionEngine.extract_handlers(nodes[0].__class__)

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
