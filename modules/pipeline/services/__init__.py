"""
Services — application logic that is NOT a queue-driven stage.

A stage is triggered by a worker pulling a job. A service is triggered by a
person: a reviewer clicking approve, an admin submitting a URL, an operator
exporting training data.

Keeping them apart matters because they have different failure semantics. A
stage may retry silently five times; an HTTP request from a reviewer must
either succeed or return an error the reviewer can act on immediately.
"""
