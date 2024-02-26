from paradise.specification import BaseSpecification
import re


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
    def get_call_arguments(call_str: str):
        """
        Call string: HandlePetition(node_id, _)
        """
        pattern = r"(Handle([A-Za-z]+))\((\d+), _(?:, (.*))?\)"
        [handler_str, message_type_str, recipient_id_str, additional_arg_str] = (
            re.findall(pattern, call_str)[0]
        )

        recipient_id = int(recipient_id_str)

        message = BaseSpecification.recv(message_type_str, int(recipient_id))
        assert message != None

        # Horribly questionable casting from string into actual datatype
        additional_arg = None
        if additional_arg_str == "":
            additional_arg = None
        elif additional_arg_str.startswith('"') and additional_arg_str.endswith('"'):
            additional_arg = additional_arg_str[1:-1]
        else:
            additional_arg = int(additional_arg_str)

        return (int(recipient_id), handler_str, message, additional_arg)

    @staticmethod
    def evaluate(
        nodes: list[BaseSpecification],
        actions: list[str],
    ):
        assert len(nodes) > 0
        handlers = ExecutionEngine.extract_handlers(nodes[0].__class__)

        for action in actions:
            (recipient_id, handler_string, message, additional_arg) = (
                ExecutionEngine.get_call_arguments(action)
            )

            assert recipient_id >= 0 and recipient_id < len(nodes)
            target_node = [node for node in nodes if node.id == recipient_id][0]

            handler = handlers[handler_string]

            if additional_arg:
                print(
                    f"For {recipient_id}, evaluating {message} with {handler.__name__}"
                )
                handler(target_node, message, additional_arg)
            else:
                print(f"For {recipient_id}, evaluating {message} with {handler}")
                handler(target_node, message)
