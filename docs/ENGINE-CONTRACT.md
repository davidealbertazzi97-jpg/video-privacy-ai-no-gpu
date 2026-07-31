# Local engine contract

An engine subclasses `LocalEngine` and is registered explicitly in
`app/engines/__init__.py`.

It receives:

- one file inside the job's private working directory;
- one dedicated durable output directory;
- a JSON-compatible options object stored with the job.

It returns a small JSON-compatible summary and paths to result artifacts. The
runner rejects artifacts outside the dedicated output directory.

An engine must:

1. work without an external network connection;
2. treat the source as untrusted and enforce its own parser and resource limits;
3. avoid including document text, credentials, or paths in exceptions and logs;
4. never mutate or delete the user's original file;
5. write temporary data under the supplied work/output boundary only;
6. use fixed argument arrays with `shell=False` for subprocesses;
7. document every dependency, model, binary, data set, and licence;
8. expose uncertainty and source evidence when producing inferred facts;
9. remain interruptible and avoid unbounded CPU, RAM, disk, or archive expansion.

The example engine performs plain text normalization and counts. It exists only
to demonstrate the contract and should be removed from a real product.
