## Paradise

...

## Requirements

Protocol object exposes:

- HandleVote(0, "foo", Vote(1, 2)), HandleMessage, etc. to users

But these are boiler-plate methods provided by the protocol writers; internally,
this method must dispatch to a parent protocol `act` method. This act method
then finds the right nodes.

Protocols can be initialized with whatever arguments, including topology type,
number of nodes, etc. They then can return a topology object so that the 
topology can be visualized.
