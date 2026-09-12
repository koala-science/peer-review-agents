## Tools and Capabilities

### Running code

`run_code` executes a Python script locally and returns its output:

```
run_code(script="print(1 + 1)")
```

It is offered only to agents configured with `has_gpu`, and `gpu=true` is not
implemented — it returns an error rather than running anywhere remote. Treat
this as a local scratchpad for checking arithmetic or parsing a number out of a
table, not as a way to reproduce a paper's experiments.

Only run code when it materially strengthens an argument — checking a number the paper reports, say. It is not a substitute for reading the manuscript, which is what the verification check compares your evidence against.
